from __future__ import annotations
import argparse, importlib, json, os, shutil, subprocess, sys, tempfile, time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; AGENT=ROOT/'conscious_agent'; TOOLS=ROOT/'tools'
def _bootstrap():
    if os.environ.get('EIDOLON_DATA_DIR'): return
    runtime=Path(tempfile.mkdtemp(prefix='eidolon-v1092-7-runtime-')); env=dict(os.environ); env['EIDOLON_DATA_DIR']=str(runtime); env['PYTHONDONTWRITEBYTECODE']='1'
    r=subprocess.run([sys.executable,str(Path(__file__).resolve()),'--child'],env=env,text=True,capture_output=True); sys.stdout.write(r.stdout); sys.stderr.write(r.stderr); raise SystemExit(r.returncode)
_bootstrap(); sys.path[:0]=[str(AGENT),str(TOOLS)]
from paths import DATA_DIR
import conversation_sessions as sessions
import project_manager
import project_recovery_state as state
import project_root_recovery as roots
import project_switching_continuity as switching
import release_metadata
import workspace_orchestration as workspace

def require(v,m):
    if not v: raise AssertionError(m)
def _root(path:Path,version='1.0'):
    path.mkdir(parents=True,exist_ok=True); (path/'PROJECT_ID').write_text('other\n'); (path/'VERSION.txt').write_text(f'VERSION={version}\n'); (path/'README.md').write_text('# Other\n'); return path
def _write(current:Path):
    for p in [DATA_DIR/'conversation_sessions',DATA_DIR/'conversation_runtime',DATA_DIR/'workspaces'/'project_switching',DATA_DIR/'workspaces'/'project_root_recovery',DATA_DIR/'workspaces'/'conversation_tabs',DATA_DIR/'memories.json']:
      if p.is_dir(): shutil.rmtree(p)
      elif p.exists(): p.unlink()
    row={'id':'other','name':'Other Project','root':str(current),'working_version':'1.0','source_identity_markers':['PROJECT_ID','README.md'],'source_version_file':'VERSION.txt','source_version_pattern':r'VERSION=([0-9.]+)','readme_path':'README.md','safe_to_modify':True}
    rows=[{'id':'eidolon','name':'Eidolon','root':str(ROOT),'working_version':release_metadata.RUNTIME_VERSION,'safe_to_modify':True},row]
    project_manager.PROJECTS_FILE.parent.mkdir(parents=True,exist_ok=True); project_manager.PROJECTS_FILE.write_text(json.dumps({'active_project_id':'other','active_project':'Other Project','projects':rows}),encoding='utf-8')
    workspace.PROJECTS_FILE.parent.mkdir(parents=True,exist_ok=True); workspace.PROJECTS_FILE.write_text(json.dumps({'projects':rows}),encoding='utf-8'); workspace.ACTIVE_PROJECT_FILE.write_text(json.dumps({'active_project_id':'other'}),encoding='utf-8')
def test_valid_preview_survives_reload_and_is_redacted():
    tmp=DATA_DIR/'valid'; old=tmp/'gone'; moved=_root(tmp/'moved'); _write(old)
    preview=roots.preview_project_root_correction('other',moved); require(preview['ok'],'preview')
    importlib.reload(roots); pending=roots.pending_project_root_correction('other')
    require(pending['pending'] and pending['valid'],'pending')
    require('preview_token' not in pending and 'candidate_source_root' not in pending,'private preview leaked')
def test_switch_revision_change_invalidates_preview():
    tmp=DATA_DIR/'revision'; old=tmp/'gone'; moved=_root(tmp/'moved'); _write(old); roots.preview_project_root_correction('other',moved)
    switching.claim_project_switch('other','eidolon',expected_revision=0,switch_key='preview-revision-change-0001')
    pending=roots.pending_project_root_correction('other'); require(not pending['valid'] and pending['status']=='stale_revision','revision not stale')
def test_identity_evidence_change_invalidates_preview():
    tmp=DATA_DIR/'identity'; old=tmp/'gone'; moved=_root(tmp/'moved'); _write(old); roots.preview_project_root_correction('other',moved)
    (moved/'VERSION.txt').write_text('VERSION=2.0\n')
    pending=roots.pending_project_root_correction('other'); require(not pending['valid'] and pending['status']=='stale_identity','identity not stale')
def test_expired_preview_is_not_pending():
    tmp=DATA_DIR/'expiry'; old=tmp/'gone'; moved=_root(tmp/'moved'); _write(old); roots.preview_project_root_correction('other',moved)
    pending=roots.pending_project_root_correction('other',now_epoch=time.time()+roots.RECOVERY_PREVIEW_TTL_SECONDS+5)
    require(not pending['pending'] and pending['status']=='expired','expiry')
def test_restart_detects_root_invalidated_while_offline():
    tmp=DATA_DIR/'offline'; current=_root(tmp/'current'); _write(current); s=sessions.create_conversation_session('Other',project_id='other'); sessions.save_conversation_draft(s['id'],'private',base_revision=0,editor_id='restart-editor')
    shutil.rmtree(current); restored=state.restore_project_recovery_state()
    require(restored['status']=='source_unavailable' and restored['controls']['conversation_enabled'],'offline root')
    require(restored['restored']['active_session_id']==s['id'] and restored['restored']['has_draft'],'state not restored')
def test_restart_restores_project_session_draft_without_replay():
    tmp=DATA_DIR/'restore'; current=_root(tmp/'current'); _write(current); s=sessions.create_conversation_session('Other',project_id='other'); sessions.save_conversation_draft(s['id'],'private',base_revision=0,editor_id='restore-editor')
    restored=project_manager.restore_active_project_continuity()
    require(restored['status']=='restart_restored' and restored['restored']['project_id']=='other','restore')
    require(restored['restored']['draft_revision']==1 and restored['restored']['has_draft'],'draft restore')
    require(not restored['accepted_turn_replayed'] and not restored['switch_replayed'] and not restored['root_correction_replayed'],'replay')
def test_confirmed_correction_discards_pending_preview():
    tmp=DATA_DIR/'confirm'; old=tmp/'gone'; moved=_root(tmp/'moved'); _write(old); preview=roots.preview_project_root_correction('other',moved)
    result=roots.confirm_project_root_correction('other',moved,preview_token=preview['preview_token'],operator_confirmed=True); require(result['ok'] and result['changed'],'confirm')
    require(roots.pending_project_root_correction('other')['status']=='none','preview retained')
def test_version_and_history_are_current():
    require(tuple(map(int, release_metadata.RUNTIME_VERSION.split('.'))) >= tuple(map(int, '1092.7'.split('.'))), 'version'); require('# v1092.7 Restart Revalidation and Recovery' in (ROOT/'README_RELEASE_HISTORY.md').read_text(), 'history'); require(not (ROOT/'data'/'projects.json').exists(),'runtime packaged')
TESTS=[(n.removeprefix('test_'),f) for n,f in list(globals().items()) if n.startswith('test_')]
def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--child',action='store_true'); parser.parse_args(); checks=[]; passed=0
    for n,f in TESTS:
      try:f()
      except Exception as e: checks.append({'name':n,'status':'fail','message':f'{type(e).__name__}: {e}'})
      else: passed+=1; checks.append({'name':n,'status':'pass','message':''})
    report={'suite':'v1092.7-restart-revalidation-recovery','ok':passed==len(TESTS),'status':'pass' if passed==len(TESTS) else 'fail','passed':passed,'total':len(TESTS),'checks':checks,'external_runtime':str(DATA_DIR)}; print(json.dumps(report,indent=2)); return 0 if report['ok'] else 1
if __name__=='__main__': raise SystemExit(main())
