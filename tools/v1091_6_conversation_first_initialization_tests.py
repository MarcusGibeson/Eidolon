from __future__ import annotations
import argparse, ast, json, os, shutil, subprocess, sys, tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; AGENT=ROOT/'conscious_agent'; TOOLS=ROOT/'tools'; sys.path[:0]=[str(AGENT),str(TOOLS)]
import dashboard_startup, release_metadata

PROVIDERS=('local_model','conversation_runtime','brain','chat')
ADMINS=('release_installation','release_packaging','controlled_build_cycle','workspace_execution','patch_drafting','conversation_daily_evaluation')
CORE=('conversation_sessions','conversation_navigation','conversation_tab_coordination','dashboard_chat_console')

def require(value,message):
    if not value: raise AssertionError(message)

def run_child(script: str, *, timeout: float=45.0) -> dict:
    runtime=Path(tempfile.mkdtemp(prefix='eidolon-v1091-6-'))
    env=os.environ.copy(); env['EIDOLON_DATA_DIR']=str(runtime); env['PYTHONDONTWRITEBYTECODE']='1'; env['PYTHONPATH']=os.pathsep.join([str(AGENT),str(TOOLS),env.get('PYTHONPATH','')])
    try:
        cp=subprocess.run([sys.executable,'-c',script],cwd=ROOT,env=env,capture_output=True,text=True,timeout=timeout)
        require(cp.returncode==0,f'child failed: {cp.stderr[-3000:]} {cp.stdout[-1500:]}')
        return json.loads(cp.stdout.strip().splitlines()[-1])
    finally:
        shutil.rmtree(runtime,ignore_errors=True)

def test_fresh_dashboard_import_keeps_conversation_provider_and_admin_unloaded():
    code="""import json,sys,dashboard
names=%r
print(json.dumps({'loaded':{n:n in sys.modules for n in names},'startup':dashboard.conversation_startup_status()}))""" % (CORE+PROVIDERS+ADMINS,)
    payload=run_child(code)
    require(not any(payload['loaded'].values()),payload)
    require(payload['startup']['status']=='uninitialized',payload)
    require(payload['startup']['provider_contacted'] is False,payload)

def test_health_then_active_session_loads_only_conversation_core():
    report=dashboard_startup.probe_dashboard_routes(ROOT,('/api/dashboard-health','/api/dashboard-chat/active-session','/api/dashboard-health'),timeout_seconds=45)
    require(report['ok'],report)
    first,active,last=report['routes']
    require(first['response_json']['conversation_startup']['status']=='uninitialized',first)
    require(active['response_json']=={'ok':True,'empty':True,'selected_session_id':'','catalog':[]},active)
    state=last['response_json']['conversation_startup']
    require(state['status'] in {'ready','degraded'} and not state['missing_core_modules'],state)
    require(not any(state['provider_modules_loaded'].values()),state)
    require(not any(state['administrative_modules_loaded'].values()),state)

def test_session_create_draft_snapshot_stays_provider_free():
    code="""import json,sys
from conversation_startup_runtime import ensure_conversation_startup
s=ensure_conversation_startup()
from conversation_sessions import create_conversation_session,save_conversation_draft
from dashboard_chat_console import dashboard_chat_session_snapshot
session=create_conversation_session('Lightweight test',source='v1091.6-test')
draft=save_conversation_draft(session['id'],'preserved local draft',editor_id='test-editor')
snapshot=dashboard_chat_session_snapshot(session['id'])
names=%r
print(json.dumps({'startup':s,'session_id':session['id'],'draft':draft,'snapshot_draft':snapshot['draft'],'loaded':{n:n in sys.modules for n in names}}))""" % (PROVIDERS+ADMINS,)
    payload=run_child(code)
    require(payload['draft']['content']=='preserved local draft',payload)
    require(payload['snapshot_draft']['content']=='preserved local draft',payload)
    require(not any(payload['loaded'].values()),payload)

def test_tab_ownership_and_exact_mutation_claim_need_no_provider():
    code="""import json,sys
from conversation_startup_runtime import ensure_conversation_startup
ensure_conversation_startup()
from conversation_tab_coordination import register_dashboard_tab,claim_dashboard_tab_mutation
owner=register_dashboard_tab('123e4567-e89b-42d3-a456-426614174000','123e4567-e89b-42d3-a456-426614174001',instance_nonce='instance-light-0001')
claim=claim_dashboard_tab_mutation(tab_id='123e4567-e89b-42d3-a456-426614174000',lease_token=owner['lease_token'],mutation_key='v1091.6-lightweight-claim',mutation_kind='select_session',session_id='',expected_revision=owner['revision'])
names=%r
print(json.dumps({'owner':owner,'claim':claim,'loaded':{n:n in sys.modules for n in names}}))""" % (PROVIDERS+ADMINS,)
    payload=run_child(code)
    require(payload['owner']['status']=='ownership_acquired',payload)
    require(payload['claim']['ok'] is True and payload['claim']['status']=='pending' and payload['claim']['coordination']['status']=='mutation_claimed',payload)
    require(not any(payload['loaded'].values()),payload)

def test_dashboard_chat_console_has_no_eager_service_imports():
    tree=ast.parse((AGENT/'dashboard_chat_console.py').read_text(encoding='utf-8'))
    allowed={'__future__','dataclasses','lazy_imports','conversation_surface_contracts','paths','release_metadata','dashboard_chat_styles'}
    eager=[node.module for node in tree.body if isinstance(node,ast.ImportFrom) and node.level==0 and node.module and node.module not in allowed and not node.module.startswith(('typing','datetime','html','pathlib'))]
    require(not eager,f'eager service imports remain: {eager}')

def test_dashboard_json_serialization_does_not_import_api_server():
    code="""import json,sys,dashboard
value=dashboard._to_jsonable({'nested':({'x':1},)})
print(json.dumps({'value':value,'api_server':'api_server' in sys.modules,'providers':{n:n in sys.modules for n in %r}}))""" % (PROVIDERS,)
    payload=run_child(code)
    require(payload['value']=={'nested':[{'x':1}]},payload)
    require(payload['api_server'] is False and not any(payload['providers'].values()),payload)

def test_conversation_runtime_import_is_deferred_until_execution():
    source=(AGENT/'conversation_recovery.py').read_text(encoding='utf-8')
    tree=ast.parse(source)
    top=[node.module for node in tree.body if isinstance(node,ast.ImportFrom)]
    require('conversation_runtime' not in top,top)
    require('from conversation_runtime import run_conversation_turn' in source,'execution-local import missing')

def test_release_metadata_docs_and_bundle_direction():
    require(tuple(int(x) for x in release_metadata.RUNTIME_VERSION.split('.')) >= (1091,6),release_metadata.RUNTIME_VERSION)
    require('v1091.6' in (ROOT/'README_RELEASE_HISTORY.md').read_text(encoding='utf-8'),'history missing v1091.6')
    require('v1150' in (ROOT/'README_NEXT_STEPS.md').read_text(encoding='utf-8'),'Codex cadence missing')

TESTS=[(n.removeprefix('test_'),f) for n,f in list(globals().items()) if n.startswith('test_')]
def main():
    argparse.ArgumentParser().add_argument('--json',action='store_true'); checks=[]; passed=0
    for name,fn in TESTS:
        try: fn()
        except Exception as exc: checks.append({'name':name,'status':'fail','message':f'{type(exc).__name__}: {exc}'})
        else: passed+=1; checks.append({'name':name,'status':'pass','message':''})
    report={'suite':'v1091.6-conversation-first-initialization','ok':passed==len(TESTS),'status':'pass' if passed==len(TESTS) else 'fail','passed':passed,'total':len(TESTS),'checks':checks}; print(json.dumps(report,indent=2)); return 0 if report['ok'] else 1
if __name__=='__main__': raise SystemExit(main())
