from __future__ import annotations
import argparse, json, os, shutil, socket, subprocess, sys, tempfile, threading, time, urllib.error, urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; AGENT=ROOT/'conscious_agent'; TOOLS=ROOT/'tools'; sys.path[:0]=[str(AGENT),str(TOOLS)]
import release_metadata

PROVIDERS=('local_model','conversation_runtime','brain','chat')
ADMINS=('release_installation','release_packaging','controlled_build_cycle','workspace_execution','patch_drafting','conversation_daily_evaluation')

def require(value,message):
    if not value: raise AssertionError(message)

def child_env(runtime: Path) -> dict[str,str]:
    env=os.environ.copy(); env['EIDOLON_DATA_DIR']=str(runtime); env['PYTHONDONTWRITEBYTECODE']='1'; env['PYTHONUNBUFFERED']='1'; env['PYTHONPATH']=os.pathsep.join([str(AGENT),str(TOOLS),env.get('PYTHONPATH','')]); return env

def run_child(script: str, *, runtime: Path|None=None, timeout: float=45.0) -> dict:
    owned=runtime is None; runtime=runtime or Path(tempfile.mkdtemp(prefix='eidolon-v1091-8-'))
    try:
        cp=subprocess.run([sys.executable,'-c',script],cwd=ROOT,env=child_env(runtime),capture_output=True,text=True,timeout=timeout)
        require(cp.returncode==0,f'child failed: {cp.stderr[-3000:]} {cp.stdout[-1500:]}')
        return json.loads(cp.stdout.strip().splitlines()[-1])
    finally:
        if owned: shutil.rmtree(runtime,ignore_errors=True)

def free_port() -> int:
    with socket.socket() as sock: sock.bind(('127.0.0.1',0)); return int(sock.getsockname()[1])

def request_json(port: int, path: str) -> tuple[int,dict]:
    req=urllib.request.Request(f'http://127.0.0.1:{port}{path}')
    try:
        with urllib.request.urlopen(req,timeout=10) as response: return int(response.status),json.loads(response.read().decode())
    except urllib.error.HTTPError as response: return int(response.code),json.loads(response.read().decode())

def start_server(runtime: Path, *, script: str|None=None):
    port=free_port(); code=script or "import dashboard; dashboard.run_dashboard('127.0.0.1',%d)"%port
    process=subprocess.Popen([sys.executable,'-c',code],cwd=ROOT,env=child_env(runtime),stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
    deadline=time.monotonic()+20
    while time.monotonic()<deadline:
        if process.poll() is not None: break
        try:
            with socket.create_connection(('127.0.0.1',port),timeout=.15): return port,process
        except OSError: time.sleep(.03)
    out,err=process.communicate(timeout=3) if process.poll() is not None else ('','')
    process.kill() if process.poll() is None else None
    raise AssertionError(f'server failed to start: {out[-1000:]} {err[-2000:]}')

def stop_server(process):
    if process.poll() is None: process.terminate()
    try: process.communicate(timeout=5)
    except subprocess.TimeoutExpired: process.kill(); process.communicate(timeout=5)

def test_required_failure_is_safe_and_next_request_recovers():
    code="""import json,sys
import conversation_startup_runtime as c
original=c.importlib.import_module
failed={'done':False}
def flaky(name,*args,**kwargs):
    if name=='conversation_sessions' and not failed['done']:
        failed['done']=True; raise ModuleNotFoundError('simulated required startup failure')
    return original(name,*args,**kwargs)
c.importlib.import_module=flaky
first=c.ensure_conversation_startup(); second=c.ensure_conversation_startup()
print(json.dumps({'first':first,'second':second,'providers':{n:n in sys.modules for n in %r}}))""" % (PROVIDERS,)
    payload=run_child(code)
    require(payload['first']['status']=='failed' and payload['first']['retry_available'] is True,payload)
    require(payload['first']['last_error_module']=='conversation_sessions',payload)
    require(payload['second']['status'] in {'ready','degraded'} and payload['second']['recoveries']>=1,payload)
    require(payload['second']['last_recovery_reason']=='retry_after_failure',payload)
    require(not any(payload['providers'].values()),payload)

def test_optional_failure_degrades_without_blocking_conversation():
    code="""import json,sys
import conversation_startup_runtime as c
original=c.importlib.import_module
def partial(name,*args,**kwargs):
    if name=='conversation_offline_durability': raise ModuleNotFoundError('optional unavailable')
    return original(name,*args,**kwargs)
c.importlib.import_module=partial
state=c.ensure_conversation_startup()
from conversation_sessions import create_conversation_session
session=create_conversation_session('degraded but usable')
print(json.dumps({'state':state,'session':session,'providers':{n:n in sys.modules for n in %r}}))""" % (PROVIDERS,)
    payload=run_child(code)
    require(payload['state']['status']=='degraded',payload)
    require(payload['state']['optional_failures'][0]['module']=='conversation_offline_durability',payload)
    require(payload['session']['title']=='degraded but usable',payload)
    require(not any(payload['providers'].values()),payload)

def test_concurrent_initialization_has_one_owner_and_one_generation():
    code="""import json,threading,time
import conversation_startup_runtime as c
original=c.importlib.import_module
calls={n:0 for n in c.CORE_CONVERSATION_MODULES}; lock=threading.Lock()
def measured(name,*args,**kwargs):
    if name in calls:
        with lock: calls[name]+=1
        time.sleep(.01)
    return original(name,*args,**kwargs)
c.importlib.import_module=measured
out=[]
def worker(): out.append(c.ensure_conversation_startup())
threads=[threading.Thread(target=worker) for _ in range(12)]
[t.start() for t in threads]; [t.join() for t in threads]
print(json.dumps({'out':out,'calls':calls,'final':c.conversation_startup_status()}))"""
    payload=run_child(code)
    require(len(payload['out'])==12,payload)
    require(payload['final']['attempts']==1 and payload['final']['generation']==1,payload)
    require(all(count==1 for count in payload['calls'].values()),payload)

def test_abandoned_owner_is_taken_over_without_replay():
    code="""import json,time
import conversation_startup_runtime as c
with c._CONDITION:
    c._STATE['status']='initializing'; c._STATE['owner_thread_id']=999999999; c._STATE['owner_token']='abandoned'; c._STATE['started_monotonic']=time.monotonic()-20
state=c.ensure_conversation_startup(stale_seconds=.05)
print(json.dumps(state))"""
    payload=run_child(code)
    require(payload['status'] in {'ready','degraded'},payload)
    require(payload['stale_takeovers']==1 and payload['recoveries']==1,payload)
    require(payload['last_recovery_reason']=='stale_initialization_owner',payload)
    require(payload['accepted_turn_replayed'] is False,payload)

def test_failed_dashboard_route_returns_safe_retryable_503():
    runtime=Path(tempfile.mkdtemp(prefix='eidolon-v1091-8-route-failure-'))
    status={'ok':False,'status':'failed','last_error_type':'ModuleNotFoundError','last_error_module':'conversation_sessions','retry_available':True,'message':'Conversation startup failed safely.','provider_contacted':False,'accepted_turn_replayed':False}
    port=free_port(); script=f"import dashboard; dashboard.ensure_conversation_startup=lambda: {status!r}; dashboard.run_dashboard('127.0.0.1',{port})"
    process=subprocess.Popen([sys.executable,'-c',script],cwd=ROOT,env=child_env(runtime),stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
    try:
        deadline=time.monotonic()+20
        while time.monotonic()<deadline:
            try:
                with socket.create_connection(('127.0.0.1',port),timeout=.1): break
            except OSError: time.sleep(.03)
        code,payload=request_json(port,'/api/dashboard-chat/active-session')
        require(code==503 and payload['retry_available'] is True,payload)
        require(payload['provider_contacted'] is False and payload['accepted_turn_replayed'] is False,payload)
    finally:
        stop_server(process); shutil.rmtree(runtime,ignore_errors=True)

def test_fresh_dashboard_process_restores_session_and_draft_without_provider():
    runtime=Path(tempfile.mkdtemp(prefix='eidolon-v1091-8-restart-'))
    try:
        created=run_child("""import json
from conversation_sessions import create_conversation_session,save_conversation_draft
s=create_conversation_session('Restart restoration',source='v1091.8-test')
d=save_conversation_draft(s['id'],'draft survives dashboard restart',editor_id='restart-test')
print(json.dumps({'session':s,'draft':d}))""",runtime=runtime)
        port,process=start_server(runtime)
        try:
            status,payload=request_json(port,'/api/dashboard-chat/active-session')
            hstatus,health=request_json(port,'/api/dashboard-health')
        finally: stop_server(process)
        require(status==200 and payload['selected_session_id']==created['session']['id'],payload)
        require(payload['snapshot']['draft']['content']=='draft survives dashboard restart',payload)
        state=health['conversation_startup']
        require(hstatus==200 and state['status'] in {'ready','degraded'},health)
        require(not any(state['provider_modules_loaded'].values()),state)
        require(not any(state['administrative_modules_loaded'].values()),state)
        require(state['accepted_turn_replayed'] is False,state)
    finally: shutil.rmtree(runtime,ignore_errors=True)

def test_recovery_status_is_content_free_and_operator_safe():
    source=(AGENT/'conversation_startup_runtime.py').read_text(encoding='utf-8')
    for forbidden in ('prompt','generated_text','credential','approval_token','provider_payload'):
        require(forbidden not in source.lower(),f'private recovery field present: {forbidden}')
    require('runtime_mutation_performed' in source and 'accepted_turn_replayed' in source,'safety flags missing')

def test_release_metadata_docs_and_checkpoint_direction():
    require(tuple(int(x) for x in release_metadata.RUNTIME_VERSION.split('.')) >= (1091,8),release_metadata.RUNTIME_VERSION)
    require(tuple(int(x) for x in release_metadata.PREVIOUS_RUNTIME_VERSION.split('.')) >= (1091,7),release_metadata.PREVIOUS_RUNTIME_VERSION)
    for name in ('README.md','archive/docs/legacy_dependencies/roadmaps/README_DESKTOP_ALPHA.md','README_NEXT_STEPS.md','README_RELEASE_HISTORY.md'):
        require('v1091.8' in (ROOT/name).read_text(encoding='utf-8'),f'{name} missing')

TESTS=[(n.removeprefix('test_'),f) for n,f in list(globals().items()) if n.startswith('test_')]
def main():
    argparse.ArgumentParser().add_argument('--json',action='store_true'); checks=[]; passed=0
    for name,fn in TESTS:
        try: fn()
        except Exception as exc: checks.append({'name':name,'status':'fail','message':f'{type(exc).__name__}: {exc}'})
        else: passed+=1; checks.append({'name':name,'status':'pass','message':''})
    report={'suite':'v1091.8-startup-failure-recovery','ok':passed==len(TESTS),'status':'pass' if passed==len(TESTS) else 'fail','passed':passed,'total':len(TESTS),'checks':checks}; print(json.dumps(report,indent=2)); return 0 if report['ok'] else 1
if __name__=='__main__': raise SystemExit(main())
