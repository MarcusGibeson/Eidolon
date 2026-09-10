from __future__ import annotations
import argparse, json, tempfile, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; AGENT=ROOT/'conscious_agent'; TOOLS=ROOT/'tools'; sys.path[:0]=[str(AGENT),str(TOOLS)]
import project_manager, release_metadata
from source_project_metadata import load_source_project_metadata

def require(value,message):
    if not value: raise AssertionError(message)

def test_packaged_identity_is_eidolon_not_milestone():
    data=load_source_project_metadata(ROOT); project=data['current_project']
    require(data['active_project']=='Eidolon' and data['active_project_id']=='eidolon','stable identity')
    require(project['name']=='Eidolon' and not project['name'].startswith('v1091.'),'milestone leaked into name')
    require(project['current_milestone']==release_metadata.RUNTIME_MILESTONE,'milestone')

def test_capabilities_and_next_steps_are_explicit():
    data=load_source_project_metadata(ROOT); project=data['current_project']
    caps=project['capabilities']; require(len(caps)>=7 and len(caps)==len(set(caps)),'capabilities')
    require('conversation_sessions_and_streaming' in caps and 'source_only_privacy_verification' in caps,'capability truth')
    require(project['next_steps'] and data['next_steps']==project['next_steps'],'next steps')

def test_legacy_single_project_milestone_name_normalizes_in_memory():
    legacy={'active_project':'v1090.9 Desktop Alpha Repair Candidate Review Checkpoint','current_milestone':'v1090.9 Desktop Alpha Repair Candidate Review Checkpoint','projects':[{'id':'eidolon','name':'Eidolon','next_steps':['continue']}]}
    normalized=project_manager._normalize_projects_data(legacy)
    require(normalized['active_project']=='Eidolon' and normalized['active_project_id']=='eidolon','legacy active identity')
    require(project_manager._resolve_active_project(normalized)['name']=='Eidolon','legacy resolution')

def test_multi_project_selection_uses_id_or_name_without_overwriting():
    data={'active_project_id':'other','active_project':'stale milestone','projects':[{'id':'eidolon','name':'Eidolon'},{'id':'other','name':'Other Project'}]}
    normalized=project_manager._normalize_projects_data(data)
    require(normalized['active_project']=='Other Project' and normalized['active_project_id']=='other','id selection')
    require([p['name'] for p in normalized['projects']]==['Eidolon','Other Project'],'project mutation')

def test_runtime_bom_projects_load_and_context_is_accurate():
    d=Path(tempfile.mkdtemp()); p=d/'projects.json'
    payload={'active_project_id':'eidolon','active_project':'v-old milestone','current_milestone':'Current Work','next_recommended_arc':'Next Work','projects':[{'id':'eidolon','name':'Eidolon','language':'Python','description':'Local mind','capabilities':['chat','memory'],'next_steps':['repair startup']}]} 
    p.write_bytes(b'\xef\xbb\xbf'+json.dumps(payload).encode())
    original=project_manager.PROJECTS_FILE
    try:
        project_manager.PROJECTS_FILE=p
        active=project_manager.get_active_project(); text=project_manager.project_context_text()
    finally: project_manager.PROJECTS_FILE=original
    require(active['name']=='Eidolon' and active['current_milestone']=='Current Work','runtime active')
    for expected in ('Active project: Eidolon','Current milestone: Current Work','Next recommended arc: Next Work','Capabilities:\n- chat','Next steps:\n- repair startup'):
        require(expected in text,expected)

def test_source_metadata_never_reads_runtime_projects_json():
    require(not (ROOT/'data'/'projects.json').exists(),'runtime projects packaged')
    data=load_source_project_metadata(ROOT); require(data['source']=='data/workspaces/projects.json' and data['runtime_projects_packaged'] is False,'source boundary')

def test_release_metadata_and_docs():
    require(tuple(int(x) for x in release_metadata.RUNTIME_VERSION.split('.')) >= (1091,1),'version')
    for name in ('README.md','archive/docs/legacy_dependencies/roadmaps/README_DESKTOP_ALPHA.md','README_NEXT_STEPS.md','README_RELEASE_HISTORY.md'):
        require('v1091.1' in (ROOT/name).read_text(encoding='utf-8'),f'{name} missing')

TESTS=[(n.removeprefix('test_'),f) for n,f in list(globals().items()) if n.startswith('test_')]
def main():
    argparse.ArgumentParser().add_argument('--json',action='store_true'); checks=[]; passed=0
    for name,fn in TESTS:
        try: fn()
        except Exception as exc: checks.append({'name':name,'status':'fail','message':f'{type(exc).__name__}: {exc}'})
        else: passed+=1; checks.append({'name':name,'status':'pass','message':''})
    report={'suite':'v1091.1-active-project-truth','ok':passed==len(TESTS),'status':'pass' if passed==len(TESTS) else 'fail','passed':passed,'total':len(TESTS),'checks':checks}; print(json.dumps(report,indent=2)); return 0 if report['ok'] else 1
if __name__=='__main__': raise SystemExit(main())
