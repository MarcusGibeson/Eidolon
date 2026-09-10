from __future__ import annotations
import argparse, ast, json, os, shutil, subprocess, sys, tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; AGENT=ROOT/'conscious_agent'; TOOLS=ROOT/'tools'; sys.path[:0]=[str(AGENT),str(TOOLS)]
import dashboard_startup, release_metadata
from dashboard_deferred_services import DEFERRED_CONSTANTS, DEFERRED_CONSTANT_SOURCES, DEFERRED_EXPORTS, DEFERRED_MODULES

ADMIN_SENTINELS=('release_installation','release_packaging','controlled_build_cycle','workspace_execution','patch_drafting','conversation_daily_evaluation')

def require(value,message):
    if not value: raise AssertionError(message)

def run_child(script: str, *, timeout: float=45.0) -> dict:
    runtime=Path(tempfile.mkdtemp(prefix='eidolon-v1091-7-'))
    env=os.environ.copy(); env['EIDOLON_DATA_DIR']=str(runtime); env['PYTHONDONTWRITEBYTECODE']='1'; env['PYTHONPATH']=os.pathsep.join([str(AGENT),str(TOOLS),env.get('PYTHONPATH','')])
    try:
        cp=subprocess.run([sys.executable,'-c',script],cwd=ROOT,env=env,capture_output=True,text=True,timeout=timeout)
        require(cp.returncode==0,f'child failed: {cp.stderr[-3000:]} {cp.stdout[-1500:]}')
        return json.loads(cp.stdout.strip().splitlines()[-1])
    finally:
        shutil.rmtree(runtime,ignore_errors=True)

def literal_from_module(module: str, name: str):
    tree=ast.parse((AGENT/f'{module}.py').read_text(encoding='utf-8'))
    for node in tree.body:
        if isinstance(node,(ast.Assign,ast.AnnAssign)):
            targets=node.targets if isinstance(node,ast.Assign) else [node.target]
            if any(isinstance(target,ast.Name) and target.id==name for target in targets):
                return ast.literal_eval(node.value)
    raise AssertionError(f'{module}.{name} not found')

def test_inventory_covers_remaining_dashboard_services_without_eager_imports():
    require(len(DEFERRED_MODULES)==125,len(DEFERRED_MODULES))
    require(sum(len(mapping) for _module,mapping in DEFERRED_EXPORTS)==608,'export count')
    require(len(DEFERRED_CONSTANTS)==81 and len(DEFERRED_CONSTANT_SOURCES)==81,'constant count')
    tree=ast.parse((AGENT/'dashboard.py').read_text(encoding='utf-8'))
    eager={node.module for node in tree.body if isinstance(node,ast.ImportFrom) and node.module in set(DEFERRED_MODULES)}
    require(not eager,f'eager deferred modules remain: {sorted(eager)}')

def test_copied_constant_contracts_match_authoritative_literals():
    mismatches=[]
    for public,(module,name) in DEFERRED_CONSTANT_SOURCES.items():
        actual=literal_from_module(module,name)
        if actual!=DEFERRED_CONSTANTS[public]: mismatches.append(public)
    require(not mismatches,f'constant drift: {mismatches}')

def test_fresh_dashboard_import_leaves_administrative_modules_unloaded():
    code="""import json,sys,dashboard
names=%r
s=dashboard.deferred_dashboard_status()
print(json.dumps({'loaded':{n:n in sys.modules for n in names},'count':s['module_count'],'resolved':s['resolved_export_count']}))""" % (ADMIN_SENTINELS,)
    payload=run_child(code)
    require(payload['count']==125,payload)
    require(payload['resolved']==0,payload)
    require(not any(payload['loaded'].values()),payload)

def test_deferred_health_then_historical_route_preserves_first_use_parity():
    report=dashboard_startup.probe_dashboard_routes(ROOT,('/api/dashboard-deferred-health','/dashboard-route-registry-extraction','/api/dashboard-deferred-health'),timeout_seconds=45)
    require(report['ok'],report)
    before,route,after=report['routes']
    require(route['status_code']==200 and 'Eidolon Dashboard' in route['body_prefix'],route)
    initial=before['response_json']['modules']['dashboard_route_registry']
    final=after['response_json']['modules']['dashboard_route_registry']
    require(initial['loaded'] is False and initial['resolved_export_count']==0,initial)
    require(final['loaded'] is True and set(final['resolved_exports'])=={'build_dashboard_route_registry_extraction_report','dashboard_route_registry_extraction_text','dashboard_route_registry_nav_items'},final)
    for name in ADMIN_SENTINELS:
        require(after['response_json']['modules'][name]['loaded'] is False,(name,after['response_json']['modules'][name]))

def test_lazy_administrative_resolution_is_thread_safe_and_singleton_bound():
    code="""import json,threading,dashboard
out=[]
def worker(): out.append(len(dashboard.dashboard_route_registry_nav_items()))
threads=[threading.Thread(target=worker) for _ in range(12)]
[t.start() for t in threads]; [t.join() for t in threads]
s=dashboard.deferred_dashboard_status()['modules']['dashboard_route_registry']
print(json.dumps({'out':out,'status':s}))"""
    payload=run_child(code)
    require(len(payload['out'])==12 and len(set(payload['out']))==1,payload)
    require(payload['status']['resolved_export_count']==1,payload)
    require(payload['status']['resolved_exports']==['dashboard_route_registry_nav_items'],payload)

def test_optional_administrative_failure_does_not_break_conversation_health():
    code="""import json,sys,dashboard,lazy_imports
original=lazy_imports.importlib.import_module
def broken(name,*args,**kwargs):
    if name=='release_installation': raise ModuleNotFoundError('optional admin unavailable')
    return original(name,*args,**kwargs)
lazy_imports.importlib.import_module=broken
failed=False
try: dashboard.build_release_profiles()
except ModuleNotFoundError: failed=True
health=dashboard.dashboard_health_payload()
print(json.dumps({'failed':failed,'health':health,'conversation':dashboard.ensure_conversation_startup()}))"""
    payload=run_child(code)
    require(payload['failed'] is True,payload)
    require(payload['health']['ok'] is True,payload)
    require(payload['conversation']['ok'] is True,payload)
    require(not any(payload['conversation']['provider_modules_loaded'].values()),payload)

def test_dashboard_chat_console_service_exports_are_lazy():
    source=(AGENT/'dashboard_chat_console.py').read_text(encoding='utf-8')
    require("install_lazy_callables" in source,'lazy installer missing')
    tree=ast.parse(source)
    top={node.module for node in tree.body if isinstance(node,ast.ImportFrom)}
    for module in ('conversation_runtime','chat_action_router','conversation_sessions','local_model','conversation_daily_evaluation'):
        require(module not in top,f'eager import remains: {module}')

def test_release_metadata_docs_and_next_version():
    require(tuple(int(x) for x in release_metadata.RUNTIME_VERSION.split('.')) >= (1091,7),release_metadata.RUNTIME_VERSION)
    require('v1091.7' in (ROOT/'README_RELEASE_HISTORY.md').read_text(encoding='utf-8'),'history missing')
    require('v1091.8' in (ROOT/'README_NEXT_STEPS.md').read_text(encoding='utf-8'),'next step missing')

TESTS=[(n.removeprefix('test_'),f) for n,f in list(globals().items()) if n.startswith('test_')]
def main():
    argparse.ArgumentParser().add_argument('--json',action='store_true'); checks=[]; passed=0
    for name,fn in TESTS:
        try: fn()
        except Exception as exc: checks.append({'name':name,'status':'fail','message':f'{type(exc).__name__}: {exc}'})
        else: passed+=1; checks.append({'name':name,'status':'pass','message':''})
    report={'suite':'v1091.7-deferred-administrative-services','ok':passed==len(TESTS),'status':'pass' if passed==len(TESTS) else 'fail','passed':passed,'total':len(TESTS),'checks':checks}; print(json.dumps(report,indent=2)); return 0 if report['ok'] else 1
if __name__=='__main__': raise SystemExit(main())
