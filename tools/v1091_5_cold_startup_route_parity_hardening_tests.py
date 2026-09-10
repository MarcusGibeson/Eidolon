from __future__ import annotations
import argparse, glob, json, os, shutil, subprocess, sys, tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; AGENT=ROOT/'conscious_agent'; TOOLS=ROOT/'tools'; sys.path[:0]=[str(AGENT),str(TOOLS)]
import dashboard_startup, release_metadata

def require(value,message):
    if not value: raise AssertionError(message)

def run_child(script: str) -> dict:
    runtime=Path(tempfile.mkdtemp(prefix='eidolon-v1091-5-'))
    env=os.environ.copy(); env['EIDOLON_DATA_DIR']=str(runtime); env['PYTHONDONTWRITEBYTECODE']='1'; env['PYTHONPATH']=os.pathsep.join([str(AGENT),env.get('PYTHONPATH','')])
    try:
        cp=subprocess.run([sys.executable,'-c',script],cwd=ROOT,env=env,capture_output=True,text=True,timeout=45)
        require(cp.returncode==0,f'child failed: {cp.stderr[-2000:]} {cp.stdout[-1000:]}')
        return json.loads(cp.stdout.strip().splitlines()[-1])
    finally:
        shutil.rmtree(runtime,ignore_errors=True)

def test_main_dashboard_fast_path_precedes_general_cli_imports():
    source=(AGENT/'main.py').read_text(encoding='utf-8')
    fast=source.index('from dashboard_launcher import launch_dashboard_from_argv')
    heavy=source.index('from chat import run_chat')
    require(fast < heavy,'dashboard fast path occurs after CLI imports')
    require((AGENT/'dashboard_launcher.py').exists(),'launcher missing')

def test_health_route_is_provider_free_and_below_target():
    report=dashboard_startup.measure_dashboard_server(ROOT,route='/api/dashboard-health',timeout_seconds=30)
    require(report['ok'] and report['below_target'],report)
    payload=report['response_json']; require(payload and tuple(int(x) for x in payload['version'].split('.')) >= (1091,5),payload)
    require(payload['provider_contacted'] is False and payload['runtime_mutation_performed'] is False,payload)
    require(all(not row['loaded'] for row in payload['lazy_modules'].values()),payload)
    require(not any(payload['general_cli_sentinels_loaded'].values()),payload)

def test_health_then_deferred_route_preserves_first_use_parity():
    report=dashboard_startup.probe_dashboard_routes(ROOT,('/api/dashboard-health','/attention','/api/dashboard-health'),timeout_seconds=45)
    require(report['ok'],report)
    first,attention,last=report['routes']
    require(first['elapsed_from_process_start_seconds'] < dashboard_startup.STARTUP_TARGET_SECONDS,first)
    require(first['response_json']['lazy_modules']['self_maintenance']['loaded'] is False,first)
    require(attention['status_code']==200 and 'Eidolon Dashboard' in attention['body_prefix'],attention)
    state=last['response_json']['lazy_modules']['self_maintenance']
    require(state['loaded'] is True and state['resolved_export_count'] >= 1,state)

def test_optional_lazy_import_failure_does_not_break_health_payload():
    code="""import json,dashboard,lazy_imports
original=lazy_imports.importlib.import_module
def broken(name,*args,**kwargs):
    if name=='self_maintenance': raise ModuleNotFoundError('optional maintenance unavailable')
    return original(name,*args,**kwargs)
lazy_imports.importlib.import_module=broken
failed=False
try: dashboard.build_controlled_attention_scheduler(save=False)
except ModuleNotFoundError: failed=True
health=dashboard.dashboard_health_payload()
print(json.dumps({'failed':failed,'health':health}))"""
    payload=run_child(code)
    require(payload['failed'] is True,payload)
    require(payload['health']['ok'] is True and payload['health']['provider_contacted'] is False,payload)

def test_cold_startup_report_uses_health_route_and_stays_below_target():
    report=dashboard_startup.build_dashboard_startup_report(ROOT,runs=3,profile_imports=True)
    require(report['ok'] and report['route']=='/api/dashboard-health',report)
    require(report['all_server_runs_below_target'] is True,report)
    require(report['maximum_first_response_seconds'] < 15.0,report)
    modules={row['module'] for row in report['import_profile']['rows']}
    require('self_maintenance' not in modules and 'self_development_cycle' not in modules,modules)

def test_port_zero_is_not_replaced_by_configured_port():
    source=(AGENT/'dashboard.py').read_text(encoding='utf-8')
    require('if port is None else int(port)' in source,'ephemeral port contract')

def test_startup_probes_remove_external_runtime_directories():
    patterns=('eidolon-dashboard-import-*','eidolon-dashboard-runtime-*','eidolon-dashboard-routes-*','eidolon-dashboard-profile-*')
    before={path for pattern in patterns for path in glob.glob(str(Path(tempfile.gettempdir())/pattern))}
    require(dashboard_startup.measure_dashboard_import(ROOT,timeout_seconds=30)['ok'],'import probe failed')
    require(dashboard_startup.measure_dashboard_server(ROOT,timeout_seconds=30)['ok'],'server probe failed')
    require(dashboard_startup.probe_dashboard_routes(ROOT,('/api/dashboard-health',),timeout_seconds=30)['ok'],'route probe failed')
    require(dashboard_startup.profile_dashboard_imports(ROOT,timeout_seconds=30)['ok'],'profile probe failed')
    after={path for pattern in patterns for path in glob.glob(str(Path(tempfile.gettempdir())/pattern))}
    require(after==before,f'probe runtime directories leaked: {sorted(after-before)}')

def test_release_metadata_docs_and_next_bundle():
    require(tuple(int(x) for x in release_metadata.RUNTIME_VERSION.split('.')) >= (1091,5),'version')
    require('v1091.5' in (ROOT/'README_RELEASE_HISTORY.md').read_text(encoding='utf-8'),'v1091.5 history missing')
    for name in ('README.md','archive/docs/legacy_dependencies/roadmaps/README_DESKTOP_ALPHA.md','README_NEXT_STEPS.md','README_RELEASE_HISTORY.md'):
        require('v1091.5' in (ROOT/name).read_text(encoding='utf-8'),f'{name} missing')

TESTS=[(n.removeprefix('test_'),f) for n,f in list(globals().items()) if n.startswith('test_')]
def main():
    argparse.ArgumentParser().add_argument('--json',action='store_true'); checks=[]; passed=0
    for name,fn in TESTS:
        try: fn()
        except Exception as exc: checks.append({'name':name,'status':'fail','message':f'{type(exc).__name__}: {exc}'})
        else: passed+=1; checks.append({'name':name,'status':'pass','message':''})
    report={'suite':'v1091.5-cold-startup-route-parity-hardening','ok':passed==len(TESTS),'status':'pass' if passed==len(TESTS) else 'fail','passed':passed,'total':len(TESTS),'checks':checks}; print(json.dumps(report,indent=2)); return 0 if report['ok'] else 1
if __name__=='__main__': raise SystemExit(main())
