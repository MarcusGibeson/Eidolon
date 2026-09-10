from __future__ import annotations
import argparse, json, os, shutil, subprocess, sys, tempfile, uuid
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; AGENT=ROOT/'conscious_agent'; TOOLS=ROOT/'tools'
def _bootstrap():
    if os.environ.get('EIDOLON_DATA_DIR'): return
    runtime=Path(tempfile.mkdtemp(prefix='eidolon-v1092-6-runtime-')); env=dict(os.environ); env['EIDOLON_DATA_DIR']=str(runtime); env['PYTHONDONTWRITEBYTECODE']='1'
    result=subprocess.run([sys.executable,str(Path(__file__).resolve()),'--child'],env=env,text=True,capture_output=True); sys.stdout.write(result.stdout); sys.stderr.write(result.stderr); raise SystemExit(result.returncode)
_bootstrap(); sys.path[:0]=[str(AGENT),str(TOOLS)]
from paths import DATA_DIR
import conversation_sessions as sessions
import conversation_tab_coordination as tabs
import project_manager
import project_recovery_state as recovery_state
import project_switching_continuity as switching
import release_metadata

def require(v,m):
    if not v: raise AssertionError(m)
def _reset(missing=False):
    for p in [DATA_DIR/'conversation_sessions',DATA_DIR/'conversation_runtime',DATA_DIR/'workspaces'/'project_switching',DATA_DIR/'workspaces'/'conversation_tabs',DATA_DIR/'memories.json']:
        if p.is_dir(): shutil.rmtree(p)
        elif p.exists(): p.unlink()
    other=DATA_DIR/'other-source'
    if other.exists(): shutil.rmtree(other)
    if not missing: other.mkdir(parents=True,exist_ok=True)
    project_manager.PROJECTS_FILE.parent.mkdir(parents=True,exist_ok=True)
    project_manager.PROJECTS_FILE.write_text(json.dumps({'active_project_id':'eidolon','active_project':'Eidolon','projects':[
      {'id':'eidolon','name':'Eidolon','root':str(ROOT),'working_version':release_metadata.RUNTIME_VERSION,'safe_to_modify':True},
      {'id':'other','name':'Other Project','root':str(other),'working_version':'1.0','safe_to_modify':False},]}),encoding='utf-8')

def test_healthy_state_consolidates_project_session_and_revision():
    _reset(); s=sessions.create_conversation_session('Work'); sessions.save_conversation_draft(s['id'],'private text',base_revision=0,editor_id='editor-one')
    state=recovery_state.build_project_recovery_state()
    require(state['status']=='healthy' and state['project']['id']=='eidolon','healthy identity')
    require(state['conversation']['active_session_id']==s['id'] and state['conversation']['has_draft'],'conversation summary')
    require(state['switch']['revision']==0 and state['provider_contacted'] is False,'switch/provider')
def test_state_never_exposes_draft_text_or_source_paths():
    _reset(); s=sessions.create_conversation_session('Work'); sessions.save_conversation_draft(s['id'],'highly private draft',base_revision=0,editor_id='editor-two')
    state=recovery_state.build_project_recovery_state(); encoded=json.dumps(state)
    require('highly private draft' not in encoded and str(ROOT) not in encoded,'private value exposed')
    require(not recovery_state.project_recovery_state_contains_private_fields(state),'private key exposed')
def test_missing_source_keeps_conversation_enabled_and_blocks_project_mutations():
    _reset(missing=True); project_manager.activate_project('other',operator_confirmed=True,expected_switch_revision=0,switch_key='missing-source-switch-0001')
    s=sessions.create_conversation_session('Unavailable',project_id='other'); sessions.save_conversation_draft(s['id'],'kept',base_revision=0,editor_id='editor-three')
    state=recovery_state.build_project_recovery_state('other')
    require(state['status']=='source_unavailable' and state['controls']['conversation_enabled'],'conversation unavailable')
    require(not state['source']['development_available'],'development incorrectly enabled')
def test_stale_tab_is_explicit_and_controls_are_disabled():
    _reset(); state=recovery_state.build_project_recovery_state(expected_switch_revision=99)
    require(state['status']=='stale_tab' and state['switch']['stale_tab'],'stale state')
    require(state['controls']['refresh_required'] and not state['controls']['project_mutations_enabled'],'stale controls')
def test_pending_switch_has_priority_without_replay():
    _reset(); claim=switching.claim_project_switch('eidolon','other',expected_revision=0,switch_key='pending-recovery-state-0001'); require(claim['ok'],'claim')
    state=recovery_state.build_project_recovery_state()
    require(state['status']=='switch_pending' and state['switch']['pending'],'pending status')
    require(not state['switch_replayed'] and not state['accepted_turn_replayed'],'replay')
def test_tab_coordination_is_content_free():
    _reset(); tab=str(uuid.uuid4()); browser=str(uuid.uuid4()); owner=tabs.register_dashboard_tab(tab,browser,instance_nonce='instance-1234567890abcdef')
    state=recovery_state.build_project_recovery_state(tab_id=tab)
    require(owner['is_owner'] and state['coordination']['is_owner'],'owner state')
    require('lease_token' not in state['coordination'],'lease leaked')
def test_project_manager_wrapper_returns_same_contract():
    _reset(); state=project_manager.active_project_recovery_state()
    require(state['type']=='project_recovery_state' and state['schema_version']=='1','wrapper')
def test_version_and_history_are_current():
    require(tuple(map(int, release_metadata.RUNTIME_VERSION.split('.'))) >= tuple(map(int, '1092.6'.split('.'))), 'version')
    require('# v1092.6 Unified Project Recovery State' in (ROOT/'README_RELEASE_HISTORY.md').read_text(encoding='utf-8'),'history')
    require(not (ROOT/'data'/'projects.json').exists(),'runtime projects packaged')
TESTS=[(n.removeprefix('test_'),f) for n,f in list(globals().items()) if n.startswith('test_')]
def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--child',action='store_true'); parser.parse_args(); checks=[]; passed=0
    for n,f in TESTS:
      try:f()
      except Exception as e: checks.append({'name':n,'status':'fail','message':f'{type(e).__name__}: {e}'})
      else: passed+=1; checks.append({'name':n,'status':'pass','message':''})
    report={'suite':'v1092.6-unified-project-recovery-state','ok':passed==len(TESTS),'status':'pass' if passed==len(TESTS) else 'fail','passed':passed,'total':len(TESTS),'checks':checks,'external_runtime':str(DATA_DIR)}; print(json.dumps(report,indent=2)); return 0 if report['ok'] else 1
if __name__=='__main__': raise SystemExit(main())
