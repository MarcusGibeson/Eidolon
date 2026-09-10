from __future__ import annotations
import hashlib, json, os, shutil, sys, tempfile, time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'conscious_agent'))
from ordinary_chat_development_campaign import create_or_resume_development_proposal, approve_development_campaign_proposal, load_development_campaign_proposal, process_ordinary_chat_development_turn
from grounded_development_planning import create_or_resume_grounded_plan, load_grounded_plan, public_grounded_plan

started=time.monotonic(); checks=[]
def req(x,d=None): checks.append(bool(x)); assert x,d
runtime=Path(tempfile.mkdtemp(prefix='eidolon-v1200-6-runtime-'))
projects=Path(tempfile.mkdtemp(prefix='eidolon-v1200-6-projects-'))
try:
    # Isolated workspace planning is automatic after exact approval.
    p=create_or_resume_development_proposal('Build me a to-do webpage',runtime_root=runtime)
    out=process_ordinary_chat_development_turn(f"Approve development proposal {p['proposal_id']} revision 1",runtime_root=runtime)
    plan=out['grounded_planning']
    req(out['event']=='approval_consumed'); req(plan['planning_status']=='grounded_plan_ready')
    req(plan['project_kind']=='new_small_web_project'); req(plan['planned_file_count']==3)
    req(plan['test_adapters']==['browser','javascript']); req(plan['inspected_file_count']==0)
    req(not plan['provider_contacted']); req(not plan['implementation_started']); req(not plan['command_executed'])
    req(not plan['selected_project_modified']); req(plan['content_free_public_projection'])
    private=load_grounded_plan(p['proposal_id'],1,runtime_root=runtime)
    req(private['specification']['objective']=='Build me a to-do webpage')
    req({x['relative_path'] for x in private['file_plan']}=={'index.html','styles.css','app.js'})
    resumed=create_or_resume_grounded_plan(p['proposal_id'],expected_revision=1,expected_revision_digest=p['revision_digest'],runtime_root=runtime)
    req(resumed['operation_status']=='resumed'); req(resumed['planning_digest']==private['planning_digest'])

    # Grounded selected project snapshot and no mutation.
    web=projects/'web'; web.mkdir();
    (web/'index.html').write_text('<main id="app"></main>',encoding='utf-8')
    (web/'app.js').write_text('export const add=(a,b)=>a+b;\n',encoding='utf-8')
    (web/'styles.css').write_text('body { font-family: sans-serif; }\n',encoding='utf-8')
    before={x.relative_to(web).as_posix():hashlib.sha256(x.read_bytes()).hexdigest() for x in web.rglob('*') if x.is_file()}
    selected=create_or_resume_development_proposal('Add a to-do list to this website',project_state={'id':'private','name':'Private Site','path':str(web)},runtime_root=runtime)
    approval=approve_development_campaign_proposal(selected['proposal_id'],revision=1,revision_digest=selected['revision_digest'],runtime_root=runtime)
    req(approval['status']=='approval_consumed')
    planned=create_or_resume_grounded_plan(selected['proposal_id'],expected_revision=1,expected_revision_digest=selected['revision_digest'],runtime_root=runtime)
    req(planned['planning_status']=='grounded_plan_ready'); req(planned['project_kind']=='javascript_or_web_project')
    req(planned['inspected_file_count']==3); req(planned['inspected_total_bytes']>0)
    req(planned['inventory_digest']); req(planned['project_snapshot_digest']); req(planned['approval_receipt_digest']==approval['receipt_digest'])
    req({x['adapter'] for x in planned['test_plan']}=={'node','browser'})
    after={x.relative_to(web).as_posix():hashlib.sha256(x.read_bytes()).hexdigest() for x in web.rglob('*') if x.is_file()}
    req(before==after); req(not any(x.suffix=='.tmp' for x in web.rglob('*')))
    pub=public_grounded_plan(planned); encoded=json.dumps(pub)
    req(str(web) not in encoded); req('Private Site' not in encoded); req('Add a to-do list' not in encoded)
    req('relative_path' not in encoded); req(pub['planned_file_digests']); req(pub['source_content_included'] is False)
    proposal=load_development_campaign_proposal(selected['proposal_id'],runtime_root=runtime)
    req(proposal['lifecycle_state']=='grounded_plan_ready'); req(proposal['grounded_plan_digest']==planned['planning_digest'])

    # Stale and approval boundaries.
    stale=create_or_resume_grounded_plan(selected['proposal_id'],expected_revision=2,expected_revision_digest='0'*64,runtime_root=runtime)
    req(stale['status']=='stale_proposal_revision')
    unapproved=create_or_resume_development_proposal('Build me a notes webpage',runtime_root=runtime)
    blocked=create_or_resume_grounded_plan(unapproved['proposal_id'],expected_revision=1,expected_revision_digest=unapproved['revision_digest'],runtime_root=runtime)
    req(blocked['status']=='approval_required'); req(not (runtime/'development_campaigns'/'planning'/unapproved['proposal_id']).exists())

    # Python detection.
    py=projects/'py'; py.mkdir(); (py/'main.py').write_text('def main():\n    return 0\n',encoding='utf-8'); (py/'pyproject.toml').write_text('[project]\nname="tiny"\n',encoding='utf-8')
    pp=create_or_resume_development_proposal('Add a command-line greeting option',project_state={'path':str(py)},runtime_root=runtime)
    approve_development_campaign_proposal(pp['proposal_id'],revision=1,revision_digest=pp['revision_digest'],runtime_root=runtime)
    pyplan=create_or_resume_grounded_plan(pp['proposal_id'],expected_revision=1,expected_revision_digest=pp['revision_digest'],runtime_root=runtime)
    req(pyplan['project_kind']=='python_project'); req([x['adapter'] for x in pyplan['test_plan']]==['python'])
    req({x['relative_path'] for x in pyplan['file_plan']}=={'main.py','tests/test_main.py'})

    # Rejections: missing path, symlink, oversized file/count/total budget.
    missing=create_or_resume_development_proposal('Fix this website',project_state={'path':str(projects/'missing')},runtime_root=runtime)
    approve_development_campaign_proposal(missing['proposal_id'],revision=1,revision_digest=missing['revision_digest'],runtime_root=runtime)
    req(create_or_resume_grounded_plan(missing['proposal_id'],expected_revision=1,expected_revision_digest=missing['revision_digest'],runtime_root=runtime)['status']=='inspection_rejected')
    over=projects/'over'; over.mkdir(); (over/'huge.js').write_bytes(b'x'*(256*1024+1))
    op=create_or_resume_development_proposal('Fix this JavaScript tool',project_state={'path':str(over)},runtime_root=runtime)
    approve_development_campaign_proposal(op['proposal_id'],revision=1,revision_digest=op['revision_digest'],runtime_root=runtime)
    ores=create_or_resume_grounded_plan(op['proposal_id'],expected_revision=1,expected_revision_digest=op['revision_digest'],runtime_root=runtime)
    req(ores['status']=='inspection_rejected'); req(ores['reason'].startswith('oversized_input:'))
    many=projects/'many'; many.mkdir()
    for i in range(201): (many/f'{i:03}.js').write_text('',encoding='utf-8')
    mp=create_or_resume_development_proposal('Fix this JavaScript tool',project_state={'path':str(many)},runtime_root=runtime)
    approve_development_campaign_proposal(mp['proposal_id'],revision=1,revision_digest=mp['revision_digest'],runtime_root=runtime)
    req(create_or_resume_grounded_plan(mp['proposal_id'],expected_revision=1,expected_revision_digest=mp['revision_digest'],runtime_root=runtime)['reason']=='project_file_count_exceeded')

    # Runtime/source separation and dashboard/API registration.
    req(all(str(x).startswith(str(runtime)) for x in (runtime/'development_campaigns'/'planning').rglob('*.json')))
    req(not (ROOT/'data'/'development_campaigns').exists())
    dashboard=(ROOT/'conscious_agent'/'dashboard.py').read_text(encoding='utf-8')
    req('/api/development-campaign/plan' in dashboard); req('public_grounded_plan' in dashboard)
    verifier=(ROOT/'tools'/'release_verify.py').read_text(encoding='utf-8')
    req(verifier.count('v1200_4_6_grounded_project_planning_tests.py')==1)
    req('v1200.6-grounded-project-planning' in verifier)
    metadata=(ROOT/'conscious_agent'/'release_metadata.py').read_text(encoding='utf-8')
    req('WORKING_SOURCE_VERSION = "1200.6"' in metadata)
finally:
    shutil.rmtree(runtime,ignore_errors=True); shutil.rmtree(projects,ignore_errors=True)
print(json.dumps({'ok':True,'suite':'v1200.4-v1200.6-grounded-project-planning','checks':len(checks),'passed':sum(checks),'elapsed_seconds':round(time.monotonic()-started,4)},sort_keys=True))
