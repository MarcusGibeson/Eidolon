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
import conversation_sessions as sessions
import file_tools, project_intelligence
from project_identity import normalize_project_identity, project_source_binding

def require(value,message):
    if not value: raise AssertionError(message)

def _runtime(tmp: Path, projects: list[dict], active='eidolon') -> Path:
    p=tmp/'projects.json'; p.write_text(json.dumps({'active_project_id':active,'projects':projects}),encoding='utf-8'); return p

def test_eidolon_source_binding_matches_exact_root_and_version():
    binding=project_manager.project_source_binding('eidolon')
    require(binding['ok'] and binding['status']=='available','binding')
    require(Path(binding['source_root'])==ROOT.resolve(),'root')
    require(binding['observed_working_version']==release_metadata.RUNTIME_VERSION,'observed version')
    require(binding['expected_working_version']==release_metadata.RUNTIME_VERSION,'expected version')
    require(binding['capability_state']['development'] is True,'development capability')

def test_missing_root_blocks_source_work_but_not_conversation():
    tmp=Path(tempfile.mkdtemp()); missing=tmp/'gone'
    runtime=_runtime(tmp,[{'id':'missing','name':'Missing Project','root':str(missing),'capabilities':['chat'],'safe_to_modify':True}],active='missing')
    original=project_manager.PROJECTS_FILE
    try:
        project_manager.PROJECTS_FILE=runtime
        binding=project_manager.project_source_binding()
        require(not binding['ok'] and binding['status']=='missing','missing binding')
        require(binding['capability_state']['ordinary_conversation'] is True,'conversation disabled')
        require(binding['capability_state']['development'] is False,'development enabled')
        session=sessions.get_active_conversation_session(create_if_missing=True)
        require(session and session['project_id']=='missing','conversation unavailable')
        try: file_tools.active_project_root()
        except FileNotFoundError: pass
        else: raise AssertionError('file tools guessed a fallback root')
    finally: project_manager.PROJECTS_FILE=original

def test_identity_marker_mismatch_is_detected():
    tmp=Path(tempfile.mkdtemp()); (tmp/'README_NEXT_STEPS.md').write_text('x')
    project=normalize_project_identity({'id':'eidolon','name':'Eidolon','root':str(tmp),'working_version':'1092.2','source_identity_markers':['conscious_agent/release_metadata.py','README_NEXT_STEPS.md'],'safe_to_modify':True},base_root=ROOT)
    binding=project_source_binding(project)
    require(not binding['ok'] and binding['status']=='identity_mismatch','marker mismatch')
    require('conscious_agent/release_metadata.py' in binding['missing_identity_markers'],'missing marker')

def test_working_version_mismatch_is_detected():
    tmp=Path(tempfile.mkdtemp()); (tmp/'conscious_agent').mkdir(); (tmp/'README_NEXT_STEPS.md').write_text('x')
    (tmp/'conscious_agent/release_metadata.py').write_text('RUNTIME_VERSION = "9999.0"\n')
    project=normalize_project_identity({'id':'eidolon','name':'Eidolon','root':str(tmp),'working_version':'1092.2','safe_to_modify':True},base_root=ROOT)
    binding=project_source_binding(project)
    require(not binding['ok'] and binding['version_mismatch'],'version mismatch')
    require(binding['observed_working_version']=='9999.0','observed')

def test_codebase_map_uses_selected_registered_root():
    tmp=Path(tempfile.mkdtemp()); project_root=tmp/'other'; project_root.mkdir(); (project_root/'sample.py').write_text('value=1\n'); (project_root/'README_NEXT_STEPS.md').write_text('# Other\n')
    runtime=_runtime(tmp,[{'id':'other','name':'Other','root':str(project_root),'working_version':'1.0','capabilities':['inspect'],'safe_to_modify':False}],active='other')
    original=project_manager.PROJECTS_FILE
    try:
        project_manager.PROJECTS_FILE=runtime
        report=project_intelligence.build_codebase_map('other')
    finally: project_manager.PROJECTS_FILE=original
    require(report['ok'] and Path(report['root'])==project_root.resolve(),'wrong root')
    require(report['file_count']==2 and report['python_file_count']==1,'file map')
    require(report['source_binding']['project_id']=='other','binding')

def test_codebase_map_blocks_missing_root_without_scanning_eidolon():
    tmp=Path(tempfile.mkdtemp()); runtime=_runtime(tmp,[{'id':'gone','name':'Gone','root':str(tmp/'missing'),'working_version':'1.0'}],active='gone')
    original=project_manager.PROJECTS_FILE
    try:
        project_manager.PROJECTS_FILE=runtime
        report=project_intelligence.build_codebase_map('gone')
    finally: project_manager.PROJECTS_FILE=original
    require(not report['ok'] and report['status']=='blocked' and report['file_count']==0,'missing scan')
    require('missing' in report['source_binding']['status'],'status')

def test_capabilities_are_project_specific():
    tmp=Path(tempfile.mkdtemp()); a=tmp/'a'; b=tmp/'b'; a.mkdir(); b.mkdir()
    runtime=_runtime(tmp,[{'id':'a','name':'A','root':str(a),'capabilities':['chat'],'safe_to_modify':False},{'id':'b','name':'B','root':str(b),'capabilities':['chat','develop'],'safe_to_modify':True}],active='a')
    original=project_manager.PROJECTS_FILE
    try:
        project_manager.PROJECTS_FILE=runtime
        one=project_manager.project_source_binding('a'); two=project_manager.project_source_binding('b')
    finally: project_manager.PROJECTS_FILE=original
    require(one['capabilities']==['chat'] and one['capability_state']['development'] is False,'a capability')
    require(two['capabilities']==['chat','develop'] and two['capability_state']['development'] is True,'b capability')

def test_release_docs_and_privacy_boundary():
    require(tuple(int(x) for x in release_metadata.RUNTIME_VERSION.split('.')) >= (1092,2),'version')
    require(str(release_metadata.NEXT_RECOMMENDED_ARC).startswith('v'),'next arc')
    require(not (ROOT/'data/projects.json').exists(),'runtime registry packaged')
    history=(ROOT/'README_RELEASE_HISTORY.md').read_text(encoding='utf-8')
    require('# v1092.2 Source-Root and Capability Binding' in history,'history entry')

TESTS=[(n.removeprefix('test_'),f) for n,f in list(globals().items()) if n.startswith('test_')]
def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--json',action='store_true'); parser.add_argument('--child',action='store_true'); parser.parse_args(); checks=[]; passed=0
    for name,fn in TESTS:
        try: fn()
        except Exception as exc: checks.append({'name':name,'status':'fail','message':f'{type(exc).__name__}: {exc}'})
        else: passed+=1; checks.append({'name':name,'status':'pass','message':''})
    report={'suite':'v1092.2-source-root-capability-binding','ok':passed==len(TESTS),'status':'pass' if passed==len(TESTS) else 'fail','passed':passed,'total':len(TESTS),'checks':checks}; print(json.dumps(report,indent=2)); return 0 if report['ok'] else 1
if __name__=='__main__': raise SystemExit(main())
