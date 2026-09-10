from __future__ import annotations
import argparse, json, os, subprocess, tempfile, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; AGENT=ROOT/'conscious_agent'; TOOLS=ROOT/'tools'
def _bootstrap_external_runtime():
    if os.environ.get('EIDOLON_DATA_DIR'): return
    runtime=Path(tempfile.mkdtemp(prefix='eidolon-v1092-legacy-runtime-')); env=dict(os.environ); env['EIDOLON_DATA_DIR']=str(runtime); env['PYTHONDONTWRITEBYTECODE']='1'
    result=subprocess.run([sys.executable,str(Path(__file__).resolve()),'--child'],env=env,text=True,capture_output=True)
    sys.stdout.write(result.stdout); sys.stderr.write(result.stderr); raise SystemExit(result.returncode)
_bootstrap_external_runtime(); sys.path[:0]=[str(AGENT),str(TOOLS)]
import project_manager, release_metadata
from project_identity import normalize_project_identity, resolve_project_selection
from source_project_metadata import load_source_project_metadata

def require(value,message):
    if not value: raise AssertionError(message)

def test_source_identity_contract_is_separated():
    data=load_source_project_metadata(ROOT); p=data['current_project']
    require(p['id']=='eidolon' and p['name']=='Eidolon','stable identity')
    require(p['identity_contract']=='project-identity-v1092','contract')
    require(p['source_root_status']=='available' and Path(p['source_root'])==ROOT.resolve(),'source root')
    require(p['working_version']==release_metadata.RUNTIME_VERSION,'working version')
    require(p['current_milestone']==release_metadata.RUNTIME_MILESTONE,'milestone')
    require(p['capabilities'] and p['next_steps'],'capabilities/next steps')

def test_milestone_cannot_replace_name():
    p=normalize_project_identity({'id':'eidolon','name':'v1092.0 Authoritative Project Identity','current_milestone':'v1092.0 Authoritative Project Identity','root':'.'},base_root=ROOT)
    require(p['name']=='Eidolon','milestone leaked')

def test_id_resolution_precedes_name():
    rows=[normalize_project_identity({'id':'alpha','name':'Shared','root':'.'},base_root=ROOT),normalize_project_identity({'id':'shared','name':'Other','root':'.'},base_root=ROOT)]
    result=resolve_project_selection(rows,'shared')
    require(result.ok and result.project['id']=='shared','id precedence')

def test_ambiguous_names_are_rejected():
    rows=[normalize_project_identity({'id':'a','name':'Same','root':'.'},base_root=ROOT),normalize_project_identity({'id':'b','name':'Same','root':'.'},base_root=ROOT)]
    result=resolve_project_selection(rows,'same').as_dict()
    require(result['status']=='ambiguous' and not result['ok'] and result['match_count']==2,'ambiguity')

def test_preview_never_rewrites_runtime_registry():
    d=Path(tempfile.mkdtemp()); runtime=d/'projects.json'
    payload={'active_project_id':'eidolon','projects':[{'id':'eidolon','name':'Eidolon','root':str(ROOT)},{'id':'other','name':'Other','root':str(d)}]}
    runtime.write_text(json.dumps(payload),encoding='utf-8'); before=runtime.read_bytes(); original=project_manager.PROJECTS_FILE
    try:
        project_manager.PROJECTS_FILE=runtime
        report=project_manager.preview_active_project_selection('other')
    finally: project_manager.PROJECTS_FILE=original
    require(report['status']=='matched' and report['operator_confirmation_required'],'preview')
    require(runtime.read_bytes()==before and report['runtime_registry_rewritten'] is False,'preview mutation')

def test_unconfirmed_activation_is_blocked():
    d=Path(tempfile.mkdtemp()); runtime=d/'projects.json'
    payload={'active_project_id':'eidolon','projects':[{'id':'eidolon','name':'Eidolon','root':str(ROOT)},{'id':'other','name':'Other','root':str(d)}]}
    runtime.write_text(json.dumps(payload),encoding='utf-8'); before=runtime.read_bytes(); original=project_manager.PROJECTS_FILE
    try:
        project_manager.PROJECTS_FILE=runtime
        report=project_manager.activate_project('other',operator_confirmed=False)
    finally: project_manager.PROJECTS_FILE=original
    require(report['status']=='confirmation_required' and not report['changed'],'confirmation')
    require(runtime.read_bytes()==before,'unconfirmed write')

def test_context_reports_exact_fields():
    text=project_manager.project_context_text(limit_items=2)
    for token in ('Active project: Eidolon','Project ID: eidolon','Source root:','Source root status: available',f'Working version: {release_metadata.RUNTIME_VERSION}',f'Current milestone: {release_metadata.RUNTIME_MILESTONE}','Capabilities:','Next steps:'):
        require(token in text,token)

def test_top_level_metadata_applies_only_to_active_project():
    normalized=project_manager._normalize_projects_data({
        'active_project_id':'eidolon',
        'working_version':'1092.2',
        'current_milestone':'Active Eidolon milestone',
        'capabilities':['active-only-capability'],
        'projects':[
            {'id':'eidolon','name':'Eidolon','root':str(ROOT)},
            {'id':'other','name':'Other','root':str(ROOT.parent/'other'),'current_milestone':'Other milestone','capabilities':['other-capability']},
        ],
    })
    rows={row['id']:row for row in normalized['projects']}
    require(rows['eidolon']['working_version']=='1092.2','active version inheritance')
    require(rows['eidolon']['current_milestone']=='Active Eidolon milestone','active milestone inheritance')
    require(rows['other']['current_milestone']=='Other milestone','inactive milestone overwritten')
    require(rows['other']['capabilities']==['other-capability'],'inactive capabilities overwritten')

def test_packaging_excludes_runtime_registry():
    require(not (ROOT/'data/projects.json').exists(),'runtime registry packaged')
    require((ROOT/'data/workspaces/projects.json').is_file(),'source-safe registry missing')

TESTS=[(n.removeprefix('test_'),f) for n,f in list(globals().items()) if n.startswith('test_')]
def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--json',action='store_true'); parser.add_argument('--child',action='store_true'); parser.parse_args(); checks=[]; passed=0
    for name,fn in TESTS:
        try: fn()
        except Exception as exc: checks.append({'name':name,'status':'fail','message':f'{type(exc).__name__}: {exc}'})
        else: passed+=1; checks.append({'name':name,'status':'pass','message':''})
    report={'suite':'v1092.0-authoritative-project-identity','ok':passed==len(TESTS),'status':'pass' if passed==len(TESTS) else 'fail','passed':passed,'total':len(TESTS),'checks':checks}; print(json.dumps(report,indent=2)); return 0 if report['ok'] else 1
if __name__=='__main__': raise SystemExit(main())
