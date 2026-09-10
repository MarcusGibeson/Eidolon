from __future__ import annotations
import argparse, hashlib, json, os, socket, subprocess, sys, tempfile, time, urllib.request
from pathlib import Path
from typing import Any
ROOT=Path(__file__).resolve().parents[1]; AGENT=ROOT/'conscious_agent'
for value in (AGENT,ROOT):
    if str(value) not in sys.path: sys.path.insert(0,str(value))
from conversational_action_portal_v1104 import build_operator_tool_catalog, action_portal_contains_private_fields
from chat_action_router import SUPERVISED_CAPABILITY_REGISTRY

def require(c:bool,d:Any='requirement failed')->None:
    if not c: raise AssertionError(d)
def snap(root:Path)->dict[str,str]:
    if not root.exists(): return {}
    return {p.relative_to(root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(root.rglob('*')) if p.is_file() and '__pycache__' not in p.parts and p.suffix not in {'.pyc','.pyo'}}
def free_port()->int:
    with socket.socket(socket.AF_INET,socket.SOCK_STREAM) as s:s.bind(('127.0.0.1',0));return int(s.getsockname()[1])
def env_for(runtime:Path,base:Path)->dict[str,str]:
    e=os.environ.copy();e.update({'EIDOLON_DATA_DIR':str(runtime),'EIDOLON_PROCESS_RUNTIME_ROOT':str(base/'process'),'EIDOLON_METADATA_LOCK_DIR':str(base/'locks'),'PYTHONDONTWRITEBYTECODE':'1','PYTHONPYCACHEPREFIX':str(base/'pycache'),'PYTHONUNBUFFERED':'1'});return e
def wait_health(port:int)->None:
    deadline=time.monotonic()+25
    while time.monotonic()<deadline:
        try:
            with urllib.request.urlopen(f'http://127.0.0.1:{port}/api/dashboard-health',timeout=.5) as r:
                if json.loads(r.read().decode()).get('service')=='eidolon-dashboard': return
        except Exception: time.sleep(.08)
    raise AssertionError('health timeout')

def test_catalog_contains_exactly_thirteen_tools()->None:
    r=build_operator_tool_catalog(); require(r['tool_count']==13,r); require(r['catalog_bounded'] is True,r); require(len(r['tools'])==13,r)
def test_catalog_ids_are_unique_and_ordered()->None:
    tools=build_operator_tool_catalog()['tools']; ids=[x['tool_id'] for x in tools]; require(len(ids)==len(set(ids)),ids); require([x['position'] for x in tools]==list(range(1,14)),tools)
def test_catalog_matches_registered_supervised_capabilities()->None:
    expected=[x['id'] for x in SUPERVISED_CAPABILITY_REGISTRY]; actual=[x['tool_id'] for x in build_operator_tool_catalog()['tools']]; require(actual==expected,(actual,expected))
def test_catalog_exposes_boundaries_without_commands_or_private_arguments()->None:
    r=build_operator_tool_catalog(); text=json.dumps(r).lower(); require(action_portal_contains_private_fields(r) is False,r); require('python conscious_agent' not in text,text); require(r['raw_commands_included'] is False and r['private_arguments_included'] is False,r)
def test_catalog_keeps_reads_and_proposals_separate()->None:
    tools=build_operator_tool_catalog()['tools']; reads=[x for x in tools if x['boundary']=='allowlisted read']; proposals=[x for x in tools if x['boundary'] in {'proposal only','isolated workspace after approval'}]; require(len(reads)==10,(len(reads),tools)); require(len(proposals)==3,(len(proposals),tools)); require(all(x['automatic_execution'] is False and x['automatic_authorization'] is False for x in tools),tools)
def test_catalog_cli_is_operator_readable_and_read_only()->None:
    base=Path(tempfile.mkdtemp(prefix='eidolon-v1104-1-cli-'));runtime=base/'runtime';runtime.mkdir(parents=True,exist_ok=True);(runtime/'existing.marker').write_text('existing runtime');before=snap(runtime);run=subprocess.run([sys.executable,str(ROOT/'eidolon.py'),'action-catalog','--json'],cwd=ROOT,env=env_for(runtime,base),capture_output=True,text=True,timeout=40);require(run.returncode==0,run.stderr);payload=json.loads(run.stdout);require(payload['tool_count']==13,payload);require(before==snap(runtime),'CLI mutated runtime')
def test_catalog_route_is_repeatable_and_runtime_read_only()->None:
    base=Path(tempfile.mkdtemp(prefix='eidolon-v1104-1-api-'));runtime=base/'runtime';port=free_port();env=env_for(runtime,base);proc=subprocess.Popen([sys.executable,str(ROOT/'eidolon.py'),'start','--no-browser','--port',str(port)],cwd=ROOT,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
    try:
        wait_health(port);before=snap(runtime);rows=[]
        for _ in range(2):
            with urllib.request.urlopen(f'http://127.0.0.1:{port}/api/conversation-action/catalog',timeout=8) as r: rows.append(json.loads(r.read().decode()))
        require(rows[0]==rows[1],rows);require(rows[0]['tool_count']==13,rows[0]);require(before==snap(runtime),'catalog route mutated runtime')
    finally:
        proc.terminate()
        try:proc.communicate(timeout=8)
        except subprocess.TimeoutExpired:proc.kill();proc.communicate(timeout=5)
TESTS=[(n.removeprefix('test_'),f) for n,f in list(globals().items()) if n.startswith('test_')]
def main()->int:
    argparse.ArgumentParser().add_argument('--json',action='store_true');checks=[];passed=0
    for name,fn in TESTS:
        try:fn()
        except Exception as e:checks.append({'name':name,'status':'fail','message':f'{type(e).__name__}: {e}'})
        else:passed+=1;checks.append({'name':name,'status':'pass','message':''})
    report={'suite':'v1104.1-bounded-operator-visible-tool-catalog','ok':passed==len(TESTS),'passed':passed,'total':len(TESTS),'checks':checks};print(json.dumps(report,indent=2));return 0 if report['ok'] else 1
if __name__=='__main__':raise SystemExit(main())
