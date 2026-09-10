from __future__ import annotations
import argparse, json, os, subprocess, sys, tempfile, threading, time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; AGENT=ROOT/'conscious_agent'; TOOLS=ROOT/'tools'; sys.path[:0]=[str(AGENT),str(TOOLS)]
import release_metadata

def require(value,message):
    if not value: raise AssertionError(message)

def fresh_dashboard_script(script: str) -> dict:
    runtime=Path(tempfile.mkdtemp(prefix='eidolon-lazy-dashboard-'))
    env=os.environ.copy(); env['EIDOLON_DATA_DIR']=str(runtime); env['PYTHONDONTWRITEBYTECODE']='1'; env['PYTHONPATH']=os.pathsep.join([str(AGENT),env.get('PYTHONPATH','')])
    cp=subprocess.run([sys.executable,'-c',script],cwd=ROOT,env=env,capture_output=True,text=True,timeout=30)
    require(cp.returncode==0,f'child failed: {cp.stderr[-2000:]} {cp.stdout[-1000:]}')
    return json.loads(cp.stdout.strip().splitlines()[-1])

def test_fresh_dashboard_defers_heavy_modules_and_imports_quickly():
    payload=fresh_dashboard_script("import json,sys,time; t=time.perf_counter(); import dashboard; print(json.dumps({'seconds':time.perf_counter()-t,'maintenance':'self_maintenance' in sys.modules,'development':'self_development_cycle' in sys.modules,'status':dashboard.lazy_import_status(['self_maintenance','self_development_cycle'])}))")
    require(payload['seconds'] < 5.0,payload)
    require(payload['maintenance'] is False and payload['development'] is False,payload)
    require(all(not row['loaded'] and row['resolved_export_count']==0 for row in payload['status'].values()),payload)

def test_lazy_export_inventory_matches_replaced_imports():
    import dashboard
    require(len(dashboard._LAZY_SELF_MAINTENANCE_EXPORTS)==474,len(dashboard._LAZY_SELF_MAINTENANCE_EXPORTS))
    require(len(dashboard._LAZY_SELF_DEVELOPMENT_CYCLE_EXPORTS)==88,len(dashboard._LAZY_SELF_DEVELOPMENT_CYCLE_EXPORTS))
    import ast
    tree=ast.parse((AGENT/'dashboard.py').read_text(encoding='utf-8'))
    eager=[node.module for node in tree.body if isinstance(node,ast.ImportFrom) and node.module in {'self_maintenance','self_development_cycle'}]
    require(not eager,f'eager top-level blocks remain: {eager}')

def test_first_use_resolves_self_development_without_runtime_lookup():
    payload=fresh_dashboard_script("import json,sys,dashboard; before='self_development_cycle' in sys.modules; phrase=dashboard.expected_self_development_patch_draft_approval_phrase({'task_result':{'task':{'id':'task-1'}},'selected':{'title':'Test'}}); status=dashboard.lazy_import_status(['self_development_cycle']); print(json.dumps({'before':before,'phrase':phrase,'status':status}))")
    require(payload['before'] is False,payload)
    require(payload['phrase'].endswith('task-1'),payload)
    row=payload['status']['self_development_cycle']; require(row['loaded'] and row['resolved_export_count']==1,row)

def test_first_use_resolves_self_maintenance_and_preserves_output():
    payload=fresh_dashboard_script("import json,sys,dashboard; before='self_maintenance' in sys.modules; text=dashboard.controlled_attention_scheduler_text({'ok':True,'status':'preview'},full=False); status=dashboard.lazy_import_status(['self_maintenance']); print(json.dumps({'before':before,'text':text,'status':status}))")
    require(payload['before'] is False,payload)
    require('Controlled Attention Scheduler' in payload['text'],payload['text'])
    row=payload['status']['self_maintenance']; require(row['loaded'] and row['resolved_export_count']==1,row)

def test_lazy_resolution_is_thread_safe():
    code="""import json,threading,dashboard
out=[]
def worker(i): out.append(dashboard.expected_self_development_patch_draft_approval_phrase({'task_result':{'task':{'id':'task-thread'}},'selected':{'title':'T'}}))
threads=[threading.Thread(target=worker,args=(i,)) for i in range(8)]
[t.start() for t in threads]; [t.join() for t in threads]
print(json.dumps({'out':out,'status':dashboard.lazy_import_status(['self_development_cycle'])}))"""
    payload=fresh_dashboard_script(code)
    require(len(payload['out'])==8 and len(set(payload['out']))==1,payload)
    require(payload['status']['self_development_cycle']['resolved_export_count']==1,payload)

def test_historical_registry_assertion_is_forward_compatible():
    text=(TOOLS/'v1091_2_cross_platform_process_verification_tests.py').read_text(encoding='utf-8')
    require("anchor=names.index('v1091.2-cross-platform-process-verification')" in text,'v1091.2 anchor missing')
    require('names[:4]==expected' not in text,'frozen prefix remains')

def test_release_metadata_and_docs():
    require(tuple(int(x) for x in release_metadata.RUNTIME_VERSION.split('.')) >= (1091,4),'version')
    for name in ('README.md','archive/docs/legacy_dependencies/roadmaps/README_DESKTOP_ALPHA.md','README_NEXT_STEPS.md','README_RELEASE_HISTORY.md'):
        require('v1091.4' in (ROOT/name).read_text(encoding='utf-8'),f'{name} missing')

TESTS=[(n.removeprefix('test_'),f) for n,f in list(globals().items()) if n.startswith('test_')]
def main():
    argparse.ArgumentParser().add_argument('--json',action='store_true'); checks=[]; passed=0
    for name,fn in TESTS:
        try: fn()
        except Exception as exc: checks.append({'name':name,'status':'fail','message':f'{type(exc).__name__}: {exc}'})
        else: passed+=1; checks.append({'name':name,'status':'pass','message':''})
    report={'suite':'v1091.4-dashboard-lazy-import-decomposition','ok':passed==len(TESTS),'status':'pass' if passed==len(TESTS) else 'fail','passed':passed,'total':len(TESTS),'checks':checks}; print(json.dumps(report,indent=2)); return 0 if report['ok'] else 1
if __name__=='__main__': raise SystemExit(main())
