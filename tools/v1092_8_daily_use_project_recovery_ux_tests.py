from __future__ import annotations
import argparse, json, os, shutil, subprocess, sys, tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; AGENT=ROOT/'conscious_agent'; TOOLS=ROOT/'tools'
def _bootstrap():
    if os.environ.get('EIDOLON_DATA_DIR'): return
    runtime=Path(tempfile.mkdtemp(prefix='eidolon-v1092-8-runtime-')); env=dict(os.environ); env['EIDOLON_DATA_DIR']=str(runtime); env['PYTHONDONTWRITEBYTECODE']='1'
    r=subprocess.run([sys.executable,str(Path(__file__).resolve()),'--child'],env=env,text=True,capture_output=True); sys.stdout.write(r.stdout); sys.stderr.write(r.stderr); raise SystemExit(r.returncode)
_bootstrap(); sys.path[:0]=[str(AGENT),str(TOOLS)]
from paths import DATA_DIR
import conversation_sessions as sessions
import dashboard_chat_console as console
import project_manager
import project_recovery_state as recovery
import release_metadata

def require(v,m):
    if not v: raise AssertionError(m)
def _reset(missing=False):
    for p in [DATA_DIR/'conversation_sessions',DATA_DIR/'conversation_runtime',DATA_DIR/'workspaces'/'project_switching',DATA_DIR/'workspaces'/'project_root_recovery',DATA_DIR/'workspaces'/'conversation_tabs',DATA_DIR/'memories.json']:
      if p.is_dir(): shutil.rmtree(p)
      elif p.exists(): p.unlink()
    other=DATA_DIR/'other-source'
    if other.exists(): shutil.rmtree(other)
    if not missing: other.mkdir(parents=True,exist_ok=True)
    project_manager.PROJECTS_FILE.parent.mkdir(parents=True,exist_ok=True); project_manager.PROJECTS_FILE.write_text(json.dumps({'active_project_id':'eidolon','active_project':'Eidolon','projects':[{'id':'eidolon','name':'Eidolon','root':str(ROOT),'working_version':release_metadata.RUNTIME_VERSION,'safe_to_modify':True},{'id':'other','name':'Other Project','root':str(other),'working_version':'1.0','safe_to_modify':False}]}),encoding='utf-8')
def test_dashboard_exposes_read_only_project_recovery_endpoint():
    source=(ROOT/'conscious_agent'/'dashboard.py').read_text(encoding='utf-8'); require('"/api/project-recovery-state"' in source,'route'); require('build_project_recovery_state' in source,'builder')
    console_source=(ROOT/'conscious_agent'/'dashboard_chat_console.py').read_text(encoding='utf-8')
    require('include_conversation_details=False' in console_source,'active-session recovery repeats the full conversation scan')
def test_chat_console_renders_understandable_project_panel():
    _reset(); sessions.create_conversation_session('Work'); html=console.render_realtime_chat_panel(None,compact=True)
    require("id='chat-project-recovery'" in html and 'Refresh project state' in html,'panel'); require('Active project' in html and 'source checking' in html,'labels')
def test_panel_does_not_expose_source_path_or_private_draft():
    _reset(); s=sessions.create_conversation_session('Work'); sessions.save_conversation_draft(s['id'],'secret recovery draft',base_revision=0,editor_id='ux-editor'); html=console.render_realtime_chat_panel(None,compact=True)
    panel=html.split("id='chat-project-recovery'",1)[1].split('</section>',1)[0]
    require(str(ROOT) not in panel and 'secret recovery draft' not in panel,'private panel')
def test_stale_revision_disables_project_bound_controls_in_client_contract():
    source=(ROOT/'conscious_agent'/'dashboard_chat_console.py').read_text(encoding='utf-8'); require("String(payload.status || '') === 'stale_tab'" in source,'stale check'); require('control.disabled = true' in source and 'projectRevisionStale' in source,'disable contract')
def test_refresh_is_provider_free_and_never_mutates_project_state():
    _reset(); before=project_manager.PROJECTS_FILE.read_bytes(); value=recovery.build_project_recovery_state(); require(value['provider_contacted'] is False,'provider'); require(project_manager.PROJECTS_FILE.read_bytes()==before,'mutation')
def test_missing_source_panel_keeps_conversation_available():
    _reset(missing=True); project_manager.activate_project('other',operator_confirmed=True,expected_switch_revision=0,switch_key='ux-missing-switch-0001'); s=sessions.create_conversation_session('Other',project_id='other'); require(s,'session')
    value=recovery.build_project_recovery_state('other'); require(value['status']=='source_unavailable' and value['controls']['conversation_enabled'],'offline UX')
def test_session_snapshot_includes_separate_recovery_state_not_spoken_text():
    _reset(); s=sessions.create_conversation_session('Work'); snap=console.dashboard_chat_session_snapshot(s['id']); require(snap['project_recovery']['type']=='project_recovery_state','snapshot'); require('project_recovery' not in snap['transcript_html'],'spoken mix')
def test_styles_cover_keyboard_and_narrow_layouts():
    styles=(ROOT/'conscious_agent'/'dashboard_chat_styles.py').read_text(encoding='utf-8'); require('.chat-project-recovery button:focus-visible' in styles,'focus'); require('@media(max-width:700px)' in styles and '.chat-project-recovery{grid-template-columns:1fr}' in styles,'narrow')
def test_version_history_and_privacy_are_current():
    require(tuple(map(int, release_metadata.RUNTIME_VERSION.split('.'))) >= (1092, 8),'version'); require(release_metadata.RUNTIME_VERSION_TAG in (ROOT/'README_RELEASE_HISTORY.md').read_text(encoding='utf-8'),'history'); require(DATA_DIR.resolve() != (ROOT/'data').resolve(),'runtime isolation')
TESTS=[(n.removeprefix('test_'),f) for n,f in list(globals().items()) if n.startswith('test_')]
def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--child',action='store_true'); parser.parse_args(); checks=[]; passed=0
    for n,f in TESTS:
      try:f()
      except Exception as e: checks.append({'name':n,'status':'fail','message':f'{type(e).__name__}: {e}'})
      else: passed+=1; checks.append({'name':n,'status':'pass','message':''})
    report={'suite':'v1092.8-daily-use-project-recovery-ux','ok':passed==len(TESTS),'status':'pass' if passed==len(TESTS) else 'fail','passed':passed,'total':len(TESTS),'checks':checks,'external_runtime':str(DATA_DIR)}; print(json.dumps(report,indent=2)); return 0 if report['ok'] else 1
if __name__=='__main__': raise SystemExit(main())
