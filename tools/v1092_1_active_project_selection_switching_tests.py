from __future__ import annotations
import argparse, contextlib, io, json, os, subprocess, tempfile, sys
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
import workspace_orchestration as workspace

def require(value,message):
    if not value: raise AssertionError(message)

def _runtime_projects(tmp: Path) -> Path:
    p=tmp/'projects.json'
    p.write_text(json.dumps({'active_project_id':'eidolon','active_project':'Eidolon','projects':[
        {'id':'eidolon','name':'Eidolon','root':str(ROOT),'capabilities':['chat','develop']},
        {'id':'other','name':'Other Project','root':str(tmp/'other'),'capabilities':['chat']},
        {'id':'same-a','name':'Same Name','root':str(tmp/'a')},
        {'id':'same-b','name':'Same Name','root':str(tmp/'b')},
    ]}),encoding='utf-8')
    (tmp/'other').mkdir(); (tmp/'a').mkdir(); (tmp/'b').mkdir()
    return p

def _with_runtime(fn):
    tmp=Path(tempfile.mkdtemp()); p=_runtime_projects(tmp); original=project_manager.PROJECTS_FILE
    try:
        project_manager.PROJECTS_FILE=p
        return fn(tmp,p)
    finally:
        project_manager.PROJECTS_FILE=original

def test_confirmed_switch_uses_stable_id():
    def run(tmp,p):
        report=project_manager.activate_project('other',operator_confirmed=True)
        data=json.loads(p.read_text())
        require(report['ok'] and report['status']=='changed','switch report')
        require(data['active_project_id']=='other' and data['active_project']=='Other Project','persisted identity')
    _with_runtime(run)

def test_unambiguous_name_switches_but_ambiguous_name_does_not():
    def run(tmp,p):
        report=project_manager.activate_project('Other Project',operator_confirmed=True)
        require(report['ok'] and report['project_id']=='other','name switch')
        before=p.read_bytes(); ambiguous=project_manager.activate_project('Same Name',operator_confirmed=True)
        require(not ambiguous['ok'] and ambiguous['status']=='ambiguous','ambiguous status')
        require(p.read_bytes()==before,'ambiguous write')
    _with_runtime(run)

def test_sessions_and_drafts_remain_project_scoped():
    def run(tmp,p):
        project_manager.activate_project('eidolon',operator_confirmed=True)
        first=sessions.create_conversation_session('Eidolon session')
        sessions.save_conversation_draft(first['id'],'eidolon draft',base_revision=0,editor_id='editor-e')
        project_manager.activate_project('other',operator_confirmed=True)
        other=sessions.get_active_conversation_session(create_if_missing=True)
        require(other['project_id']=='other' and other['id']!=first['id'],'other session')
        require(sessions.load_conversation_draft(other['id'])['content']=='','draft leak')
        sessions.save_conversation_draft(other['id'],'other draft',base_revision=0,editor_id='editor-o')
        project_manager.activate_project('eidolon',operator_confirmed=True)
        restored=sessions.get_active_conversation_session(create_if_missing=False)
        require(restored and restored['id']==first['id'] and restored['project_id']=='eidolon','eidolon restoration')
        require(sessions.load_conversation_draft(restored['id'])['content']=='eidolon draft','eidolon draft restoration')
        project_manager.activate_project('other',operator_confirmed=True)
        restored_other=sessions.get_active_conversation_session(create_if_missing=False)
        require(restored_other and restored_other['id']==other['id'],'other restoration')
        require(sessions.load_conversation_draft(restored_other['id'])['content']=='other draft','other draft restoration')
    _with_runtime(run)

def test_cross_project_session_selection_is_blocked():
    def run(tmp,p):
        project_manager.activate_project('eidolon',operator_confirmed=True)
        first=sessions.create_conversation_session('Bound session')
        project_manager.activate_project('other',operator_confirmed=True)
        try: sessions.select_conversation_session(first['id'])
        except ValueError as exc: require('different active project' in str(exc),'wrong error')
        else: raise AssertionError('cross-project session selected')
    _with_runtime(run)

def test_session_lists_filter_by_project_id():
    def run(tmp,p):
        project_manager.activate_project('eidolon',operator_confirmed=True); e=sessions.create_conversation_session('E')
        project_manager.activate_project('other',operator_confirmed=True); o=sessions.create_conversation_session('O')
        eids={row['id'] for row in sessions.list_conversation_sessions(project_id='eidolon')}
        oids={row['id'] for row in sessions.list_conversation_sessions(project_id='other')}
        require(e['id'] in eids and o['id'] not in eids,'eidolon filter')
        require(o['id'] in oids and e['id'] not in oids,'other filter')
    _with_runtime(run)

def test_active_pointer_is_content_free_and_per_project():
    def run(tmp,p):
        project_manager.activate_project('eidolon',operator_confirmed=True); e=sessions.create_conversation_session('E')
        project_manager.activate_project('other',operator_confirmed=True); o=sessions.create_conversation_session('O')
        pointer=json.loads(sessions.ACTIVE_SESSION_FILE.read_text())
        require(pointer['projects']['eidolon']==e['id'] and pointer['projects']['other']==o['id'],'project map')
        require(pointer['content_free'] is True and pointer['local_private'] is True,'pointer flags')
        for forbidden in ('content','draft','transcript','provider','model','prompt'):
            require(forbidden not in pointer,forbidden)
    _with_runtime(run)

def test_workspace_registry_misalignment_blocks_pointer_change_and_cli_confirms():
    tmp=Path(tempfile.mkdtemp())
    workspace_registry=tmp/'workspace-projects.json'
    workspace_active=tmp/'workspace-active.json'
    runtime_registry=tmp/'runtime-projects.json'
    workspace_registry.write_text(json.dumps({'projects':[
        {'id':'eidolon','name':'Eidolon','root':str(ROOT)},
        {'id':'other','name':'Other Project','root':str(tmp/'other')},
    ]}),encoding='utf-8')
    runtime_registry.write_text(json.dumps({'active_project_id':'eidolon','projects':[
        {'id':'eidolon','name':'Eidolon','root':str(ROOT)},
    ]}),encoding='utf-8')
    workspace_active.write_text(json.dumps({'active_project_id':'eidolon'}),encoding='utf-8')
    originals=(workspace.PROJECTS_FILE,workspace.ACTIVE_PROJECT_FILE,project_manager.PROJECTS_FILE)
    try:
        workspace.PROJECTS_FILE=workspace_registry
        workspace.ACTIVE_PROJECT_FILE=workspace_active
        project_manager.PROJECTS_FILE=runtime_registry
        before=workspace_active.read_bytes()
        report=workspace.set_active_workspace_project('other',operator_confirmed=True)
        require(not report['ok'] and report['status']=='blocked','unaligned registry not blocked')
        require(workspace_active.read_bytes()==before,'workspace pointer changed despite runtime rejection')

        captured={}
        original_setter=workspace.set_active_workspace_project
        def fake_setter(project_id,*,operator_confirmed=False):
            captured.update(project_id=project_id,operator_confirmed=operator_confirmed)
            return {'ok':True,'status':'changed','rows':[]}
        workspace.set_active_workspace_project=fake_setter
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                workspace.print_set_active_workspace_project('eidolon',json_output=True)
        finally:
            workspace.set_active_workspace_project=original_setter
        require(captured=={'project_id':'eidolon','operator_confirmed':True},'explicit CLI did not confirm exact mutation')
    finally:
        workspace.PROJECTS_FILE,workspace.ACTIVE_PROJECT_FILE,project_manager.PROJECTS_FILE=originals

def test_legacy_session_without_project_id_remains_eidolon_compatible():
    legacy_id=sessions.new_conversation_session_id(); now='2026-07-23T12:00:00Z'
    record={'id':legacy_id,'type':'conversation_session','schema_version':'1','title':'Legacy','created_at':now,'updated_at':now,'status':'active','turns':[]}
    sessions._atomic_write(sessions._session_path(legacy_id),record)
    loaded=sessions.load_conversation_session(legacy_id,include_turns=False)
    require(sessions._session_project_id(loaded)=='eidolon','legacy binding')

def test_release_and_source_boundaries():
    require(tuple(int(x) for x in release_metadata.RUNTIME_VERSION.split('.')) >= (1092,1),'version')
    require(not (ROOT/'data/projects.json').exists(),'runtime registry packaged')
    require('v1092.1' in (ROOT/'README_RELEASE_HISTORY.md').read_text(encoding='utf-8'),'history')

TESTS=[(n.removeprefix('test_'),f) for n,f in list(globals().items()) if n.startswith('test_')]
def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--json',action='store_true'); parser.add_argument('--child',action='store_true'); parser.parse_args(); checks=[]; passed=0
    for name,fn in TESTS:
        try: fn()
        except Exception as exc: checks.append({'name':name,'status':'fail','message':f'{type(exc).__name__}: {exc}'})
        else: passed+=1; checks.append({'name':name,'status':'pass','message':''})
    report={'suite':'v1092.1-active-project-selection-switching','ok':passed==len(TESTS),'status':'pass' if passed==len(TESTS) else 'fail','passed':passed,'total':len(TESTS),'checks':checks}; print(json.dumps(report,indent=2)); return 0 if report['ok'] else 1
if __name__=='__main__': raise SystemExit(main())
