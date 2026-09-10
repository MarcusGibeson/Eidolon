from __future__ import annotations
import json, shutil, sys, tempfile, time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/'conscious_agent'))
from ordinary_chat_development_campaign import create_or_resume_development_proposal, approve_development_campaign_proposal
from grounded_development_planning import create_or_resume_grounded_plan
from structured_development_generation import generate_or_resume_structured_output
from isolated_implementation_workspace import materialize_or_resume_workspace, public_workspace
start=time.monotonic(); checks=[]
def req(x,d=None): checks.append(bool(x)); assert x,d
runtime=Path(tempfile.mkdtemp(prefix='eidolon-v1201-2-runtime-'))
try:
 p=create_or_resume_development_proposal('Build me a to-do webpage',runtime_root=runtime); approve_development_campaign_proposal(p['proposal_id'],revision=1,revision_digest=p['revision_digest'],runtime_root=runtime); plan=create_or_resume_grounded_plan(p['proposal_id'],expected_revision=1,expected_revision_digest=p['revision_digest'],runtime_root=runtime)
 authority={'proposal_id':p['proposal_id'],'revision':1,'revision_digest':p['revision_digest'],'planning_digest':plan['planning_digest'],'project_snapshot_digest':plan['project_snapshot_digest']}; payload={'authority':authority,'files':[{'path':'index.html','operation':'create','content':'<!doctype html><main id="app"></main>'},{'path':'styles.css','operation':'create','content':'body { font-family: sans-serif; }'},{'path':'app.js','operation':'create','content':'const tasks = [];\n'}]}
 gen=generate_or_resume_structured_output(p['proposal_id'],expected_revision=1,expected_revision_digest=p['revision_digest'],expected_planning_digest=plan['planning_digest'],runtime_root=runtime,provider_generate=lambda _:json.dumps(payload))
 out=materialize_or_resume_workspace(p['proposal_id'],expected_revision=1,expected_revision_digest=p['revision_digest'],expected_planning_digest=plan['planning_digest'],expected_generation_digest=gen['generation_digest'],runtime_root=runtime)
 req(out['status']=='isolated_workspace_ready'); req(out['file_count']==3); root=Path(out['workspace_path']); req(root.is_dir()); req((root/'index.html').read_text().startswith('<!doctype')); req(not out['selected_project_modified']); req(not out['command_executed']); req(not out['tests_executed']); req(not out['authority_granted'])
 resumed=materialize_or_resume_workspace(p['proposal_id'],expected_revision=1,expected_revision_digest=p['revision_digest'],expected_planning_digest=plan['planning_digest'],expected_generation_digest=gen['generation_digest'],runtime_root=runtime); req(resumed['operation_status']=='resumed'); req(resumed['workspace_digest']==out['workspace_digest'])
 pub=public_workspace(out); enc=json.dumps(pub); req(str(root) not in enc); req('index.html' not in enc); req(not pub['workspace_path_exposed']); req(pub['file_count']==3)
 (root/'index.html').write_text('tampered'); bad=materialize_or_resume_workspace(p['proposal_id'],expected_revision=1,expected_revision_digest=p['revision_digest'],expected_planning_digest=plan['planning_digest'],expected_generation_digest=gen['generation_digest'],runtime_root=runtime); req(bad['status']=='workspace_record_invalid')
 # selected project is copied but never changed
 project=Path(tempfile.mkdtemp(prefix='eidolon-selected-project-')); (project/'index.html').write_text('old'); original=(project/'index.html').read_bytes(); r2=runtime/'second'; q=create_or_resume_development_proposal('Edit this website',project_state={'id':'p1','path':str(project)},runtime_root=r2); approve_development_campaign_proposal(q['proposal_id'],revision=1,revision_digest=q['revision_digest'],runtime_root=r2); pl=create_or_resume_grounded_plan(q['proposal_id'],expected_revision=1,expected_revision_digest=q['revision_digest'],runtime_root=r2); au={'proposal_id':q['proposal_id'],'revision':1,'revision_digest':q['revision_digest'],'planning_digest':pl['planning_digest'],'project_snapshot_digest':pl['project_snapshot_digest']}; data={'authority':au,'files':[{'path':x['relative_path'],'operation':x['operation'],'content':'new' if x['operation']!='delete' else ''} for x in pl['file_plan']]}; ge=generate_or_resume_structured_output(q['proposal_id'],expected_revision=1,expected_revision_digest=q['revision_digest'],expected_planning_digest=pl['planning_digest'],runtime_root=r2,provider_generate=lambda _:json.dumps(data)); wo=materialize_or_resume_workspace(q['proposal_id'],expected_revision=1,expected_revision_digest=q['revision_digest'],expected_planning_digest=pl['planning_digest'],expected_generation_digest=ge['generation_digest'],runtime_root=r2); req(wo['ok']); req((project/'index.html').read_bytes()==original); req(Path(wo['workspace_path']).resolve()!=project.resolve())
 shutil.rmtree(project,ignore_errors=True)
 req(not (ROOT/'data'/'development_campaigns').exists())
finally: shutil.rmtree(runtime,ignore_errors=True)
print(json.dumps({'ok':True,'suite':'v1201.0-v1201.2-isolated-workspace-materialization','checks':len(checks),'passed':sum(checks),'elapsed_seconds':round(time.monotonic()-start,4)},sort_keys=True))
