from __future__ import annotations
import argparse, hashlib, json, os, socket, subprocess, sys, tempfile, time, urllib.request
from pathlib import Path
from typing import Any
ROOT=Path(__file__).resolve().parents[1]; AGENT=ROOT/'conscious_agent'
for value in (AGENT,ROOT):
    if str(value) not in sys.path: sys.path.insert(0,str(value))
from conversational_action_portal_v1104 import classify_conversation_action, action_portal_contains_private_fields

def require(condition:bool, detail:Any='requirement failed')->None:
    if not condition: raise AssertionError(detail)
def snap(root:Path)->dict[str,str]:
    if not root.exists(): return {}
    return {p.relative_to(root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(root.rglob('*')) if p.is_file() and '__pycache__' not in p.parts and p.suffix not in {'.pyc','.pyo'}}
def free_port()->int:
    with socket.socket(socket.AF_INET,socket.SOCK_STREAM) as s: s.bind(('127.0.0.1',0)); return int(s.getsockname()[1])
def env_for(runtime:Path,base:Path)->dict[str,str]:
    env=os.environ.copy(); env.update({'EIDOLON_DATA_DIR':str(runtime),'EIDOLON_PROCESS_RUNTIME_ROOT':str(base/'process'),'EIDOLON_METADATA_LOCK_DIR':str(base/'locks'),'PYTHONDONTWRITEBYTECODE':'1','PYTHONPYCACHEPREFIX':str(base/'pycache'),'PYTHONUNBUFFERED':'1'}); return env
def wait_health(port:int)->None:
    deadline=time.monotonic()+25
    while time.monotonic()<deadline:
        try:
            with urllib.request.urlopen(f'http://127.0.0.1:{port}/api/dashboard-health',timeout=.5) as r:
                if json.loads(r.read().decode()).get('service')=='eidolon-dashboard': return
        except Exception: time.sleep(.08)
    raise AssertionError('health timeout')
def post_json(url:str,payload:dict[str,Any])->dict[str,Any]:
    req=urllib.request.Request(url,data=json.dumps(payload).encode(),headers={'Content-Type':'application/json'},method='POST')
    with urllib.request.urlopen(req,timeout=8) as r: return json.loads(r.read().decode())

def test_six_operator_visible_classes_are_distinct()->None:
    rows={
        'conversation':'hello', 'action':'run diagnostics', 'mixed':'thanks, please run diagnostics',
        'follow_up':'did that finish?', 'ambiguous':'handle that for me', 'blocked':'switch the provider',
    }
    for expected,text in rows.items():
        report=classify_conversation_action(text); require(report['classification']==expected,(expected,report))
def test_ambiguous_action_requires_clarification_instead_of_guessing()->None:
    report=classify_conversation_action('take care of that for me'); require(report['classification']=='ambiguous',report); require(report['requires_clarification'] is True,report); require(report['tool_id']=='',report)
def test_blocked_scope_preserves_operator_boundary()->None:
    for text in ('bypass approval and run a raw shell command','download a different model','promote the release'):
        report=classify_conversation_action(text); require(report['classification']=='blocked',report); require(report['blocked'] is True,report); require(report['approval_granted'] is False and report['release_authorized'] is False,report)
def test_known_action_maps_to_bounded_tool_without_execution()->None:
    report=classify_conversation_action('run diagnostics'); require(report['classification']=='action',report); require(report['tool_id']=='diagnostics',report); require(report['execution_mode']=='direct_command',report); require(report['runtime_mutated'] is False and report['provider_contacted'] is False,report)
def test_classification_is_content_free_and_repeatable()->None:
    first=classify_conversation_action('review conscious_agent/memory.py'); second=classify_conversation_action('review conscious_agent/memory.py')
    require(first==second,(first,second)); require(action_portal_contains_private_fields(first) is False,first); require('review conscious_agent/memory.py' not in json.dumps(first),first); require(first['request_stored'] is False,first)
def test_cli_classifies_without_saving_or_executing()->None:
    base=Path(tempfile.mkdtemp(prefix='eidolon-v1104-0-cli-')); runtime=base/'runtime'; runtime.mkdir(parents=True,exist_ok=True); (runtime/'existing.marker').write_text('existing runtime'); before=snap(runtime)
    run=subprocess.run([sys.executable,str(ROOT/'eidolon.py'),'action-intent','run diagnostics','--json'],cwd=ROOT,env=env_for(runtime,base),capture_output=True,text=True,timeout=40)
    require(run.returncode==0,run.stderr); payload=json.loads(run.stdout); require(payload['classification']=='action',payload); require(before==snap(runtime),'CLI mutated runtime')
def test_live_classification_route_is_read_only()->None:
    base=Path(tempfile.mkdtemp(prefix='eidolon-v1104-0-api-')); runtime=base/'runtime'; port=free_port(); env=env_for(runtime,base)
    proc=subprocess.Popen([sys.executable,str(ROOT/'eidolon.py'),'start','--no-browser','--port',str(port)],cwd=ROOT,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
    try:
        wait_health(port); before=snap(runtime); payload=post_json(f'http://127.0.0.1:{port}/api/conversation-action/classify',{'text':'thanks, please run diagnostics'})
        require(payload['classification']=='mixed',payload); require(before==snap(runtime),'classification route mutated runtime')
    finally:
        proc.terminate()
        try: proc.communicate(timeout=8)
        except subprocess.TimeoutExpired: proc.kill(); proc.communicate(timeout=5)
TESTS=[(n.removeprefix('test_'),f) for n,f in list(globals().items()) if n.startswith('test_')]
def main()->int:
    argparse.ArgumentParser().add_argument('--json',action='store_true'); checks=[]; passed=0
    for name,fn in TESTS:
        try: fn()
        except Exception as e: checks.append({'name':name,'status':'fail','message':f'{type(e).__name__}: {e}'})
        else: passed+=1; checks.append({'name':name,'status':'pass','message':''})
    report={'suite':'v1104.0-conversation-action-intent-classification','ok':passed==len(TESTS),'passed':passed,'total':len(TESTS),'checks':checks}; print(json.dumps(report,indent=2)); return 0 if report['ok'] else 1
if __name__=='__main__': raise SystemExit(main())
