from __future__ import annotations
import argparse, json, tempfile, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; AGENT=ROOT/'conscious_agent'; TOOLS=ROOT/'tools'; sys.path[:0]=[str(AGENT),str(TOOLS)]
import json_storage, memory, project_manager, release_metadata

def require(value,message):
    if not value: raise AssertionError(message)

def test_bom_aware_loader_accepts_dict_and_list():
    d=Path(tempfile.mkdtemp()); a=d/'object.json'; b=d/'list.json'
    a.write_bytes(b'\xef\xbb\xbf'+json.dumps({'name':'Eidolon','value':'\u2603'}).encode('utf-8'))
    b.write_bytes(b'\xef\xbb\xbf'+json.dumps([1,2,3]).encode('utf-8'))
    require(json_storage.load_json_file(a,{},expected_type=dict)['name']=='Eidolon','dict BOM load')
    require(memory.load_json(b,[])==[1,2,3],'shared runtime BOM load')

def test_invalid_or_wrong_shape_preserves_independent_default():
    d=Path(tempfile.mkdtemp()); p=d/'bad.json'; p.write_text('{broken',encoding='utf-8')
    default={'items':[]}; first=json_storage.load_json_file(p,default,expected_type=dict); first['items'].append('x')
    second=json_storage.load_json_file(p,default,expected_type=dict)
    require(second=={'items':[]},'default was shared or corrupted')
    p.write_text('[]',encoding='utf-8'); require(json_storage.load_json_file(p,{'safe':True},expected_type=dict)=={'safe':True},'shape guard')

def test_atomic_save_is_utf8_without_bom():
    d=Path(tempfile.mkdtemp()); p=d/'state.json'; memory.save_json(p,{'text':'café','nested':[1,2]})
    raw=p.read_bytes(); require(not raw.startswith(json_storage.UTF8_BOM),'BOM written'); require(json.loads(raw.decode('utf-8'))['text']=='café','round trip')
    require(not list(d.glob('*.tmp')) and not list(d.glob('.*.tmp')),'temporary file leaked')

def test_migration_refuses_without_confirmation():
    d=Path(tempfile.mkdtemp()); p=d/'projects.json'; raw=b'\xef\xbb\xbf{"active_project":"Eidolon","projects":[]}' ; p.write_bytes(raw)
    result=json_storage.migrate_json_file_encoding(p,operator_confirmed=False,expected_type=dict)
    require(result['status']=='confirmation_required' and not result['ok'],'unguarded migration')
    require(p.read_bytes()==raw,'unconfirmed mutation')

def test_confirmed_migration_is_backup_bound_and_verified():
    d=Path(tempfile.mkdtemp()); p=d/'projects.json'; p.write_bytes(b'\xef\xbb\xbf'+json.dumps({'active_project':'Eidolon','projects':[]}).encode())
    result=json_storage.migrate_json_file_encoding(p,operator_confirmed=True,expected_type=dict)
    require(result['ok'] and result['status']=='migrated','migration failed')
    require(result['backup_created'] and not result['utf8_bom_present_after'],'migration evidence')
    backups=list(d.glob('.projects.json.pre-utf8-migration-*.bak')); require(len(backups)==1 and backups[0].read_bytes().startswith(json_storage.UTF8_BOM),'backup missing')
    require(json.loads(p.read_text(encoding='utf-8'))['active_project']=='Eidolon','payload drift')

def test_project_manager_migration_targets_only_runtime_file():
    d=Path(tempfile.mkdtemp()); p=d/'projects.json'; p.write_bytes(b'\xef\xbb\xbf{"active_project":"Eidolon","projects":[]}')
    original=project_manager.PROJECTS_FILE
    try:
        project_manager.PROJECTS_FILE=p
        denied=project_manager.migrate_projects_metadata_encoding(operator_confirmed=False)
        allowed=project_manager.migrate_projects_metadata_encoding(operator_confirmed=True)
    finally: project_manager.PROJECTS_FILE=original
    require(denied['status']=='confirmation_required' and allowed['ok'],'project migration boundary')

def test_release_metadata_and_docs():
    require(tuple(int(x) for x in release_metadata.RUNTIME_VERSION.split('.')) >= (1091,0),'version')
    for name in ('README.md','archive/docs/legacy_dependencies/roadmaps/README_DESKTOP_ALPHA.md','README_NEXT_STEPS.md','README_RELEASE_HISTORY.md'):
        require('v1091.0' in (ROOT/name).read_text(encoding='utf-8'),f'{name} missing')

def test_source_only_boundary():
    relative={p.relative_to(ROOT).as_posix() for p in ROOT.rglob('*')}
    forbidden={'data/projects.json','data/tasks.json','data/memories.json','.git','.venv','venv'}
    require(not (relative&forbidden),str(relative&forbidden))

TESTS=[(n.removeprefix('test_'),f) for n,f in list(globals().items()) if n.startswith('test_')]
def main():
    argparse.ArgumentParser().add_argument('--json',action='store_true'); checks=[]; passed=0
    for name,fn in TESTS:
        try: fn()
        except Exception as exc: checks.append({'name':name,'status':'fail','message':f'{type(exc).__name__}: {exc}'})
        else: passed+=1; checks.append({'name':name,'status':'pass','message':''})
    report={'suite':'v1091.0-bom-aware-json-metadata-migration','ok':passed==len(TESTS),'status':'pass' if passed==len(TESTS) else 'fail','passed':passed,'total':len(TESTS),'checks':checks}
    print(json.dumps(report,indent=2)); return 0 if report['ok'] else 1
if __name__=='__main__': raise SystemExit(main())
