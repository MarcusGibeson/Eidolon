from __future__ import annotations
import argparse, hashlib, json, os, re, socket, subprocess, sys, tempfile, time, urllib.request
from pathlib import Path
from typing import Any
ROOT=Path(__file__).resolve().parents[1];AGENT=ROOT/'conscious_agent'
for value in (AGENT,ROOT):
    if str(value) not in sys.path:sys.path.insert(0,str(value))
from conversational_action_portal_v1104 import build_action_proposal_card, action_portal_contains_private_fields
from dashboard_first_use import render_first_use_shell

def require(c:bool,d:Any='requirement failed')->None:
    if not c:raise AssertionError(d)
def snap(root:Path)->dict[str,str]:
    if not root.exists():return {}
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
                if json.loads(r.read().decode()).get('service')=='eidolon-dashboard':return
        except Exception:time.sleep(.08)
    raise AssertionError('health timeout')
def post(url:str,payload:dict[str,Any])->dict[str,Any]:
    req=urllib.request.Request(url,data=json.dumps(payload).encode(),headers={'Content-Type':'application/json'},method='POST')
    with urllib.request.urlopen(req,timeout=8) as r:return json.loads(r.read().decode())

def test_low_risk_read_card_explains_scope_before_execution()->None:
    r=build_action_proposal_card('run diagnostics');require(r['card_type']=='action_proposal',r);require(r['tool_id']=='diagnostics',r);require(r['risk_level']=='low',r);require(r['will_execute'] is False and r['execution_timing'].startswith('only_after_visible'),r)
def test_write_card_requires_separate_approval()->None:
    r=build_action_proposal_card('apply latest patch');require(r['card_type']=='approval_proposal',r);require(r['approval_required'] is True,r);require(r['execution_timing']=='only_after_separate_explicit_approval',r);require(r['approval_granted'] is False,r)
def test_blocked_and_ambiguous_cards_do_not_select_tools_by_guessing()->None:
    blocked=build_action_proposal_card('switch the provider');ambiguous=build_action_proposal_card('do that')
    require(blocked['card_type']=='blocked_request' and blocked['tool_id']=='',blocked);require(ambiguous['card_type']=='clarification_required' and ambiguous['tool_id']=='',ambiguous)
def test_conversation_and_mixed_turns_remain_distinct()->None:
    conversation=build_action_proposal_card('hello');mixed=build_action_proposal_card('thanks, please run diagnostics')
    require(conversation['card_type']=='conversation_only',conversation);require(mixed['classification']=='mixed' and mixed['card_type']=='action_proposal',mixed)
def test_cards_are_redacted_non_authorizing_and_command_free()->None:
    r=build_action_proposal_card('review conscious_agent/memory.py');text=json.dumps(r).lower();require(action_portal_contains_private_fields(r) is False,r);require('conscious_agent/memory.py' not in text,text);require(r['raw_command_included'] is False and r['private_arguments_included'] is False,r);require(all(r[k] is False for k in ('will_execute','runtime_mutated','provider_contacted','approval_granted','release_authorized')),r)
def test_cli_and_live_route_are_repeatable_and_runtime_read_only()->None:
    base=Path(tempfile.mkdtemp(prefix='eidolon-v1104-2-live-'));runtime=base/'runtime';runtime.mkdir(parents=True,exist_ok=True);(runtime/'existing.marker').write_text('existing runtime');env=env_for(runtime,base);before=snap(runtime)
    cli=subprocess.run([sys.executable,str(ROOT/'eidolon.py'),'action-preview','run diagnostics','--json'],cwd=ROOT,env=env,capture_output=True,text=True,timeout=40);require(cli.returncode==0,cli.stderr);require(json.loads(cli.stdout)['card_type']=='action_proposal',cli.stdout);require(before==snap(runtime),'CLI mutated runtime')
    port=free_port();proc=subprocess.Popen([sys.executable,str(ROOT/'eidolon.py'),'start','--no-browser','--port',str(port)],cwd=ROOT,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
    try:
        wait_health(port);before=snap(runtime);one=post(f'http://127.0.0.1:{port}/api/conversation-action/proposal',{'text':'apply latest patch'});two=post(f'http://127.0.0.1:{port}/api/conversation-action/proposal',{'text':'apply latest patch'});require(one==two,(one,two));require(one['card_type']=='approval_proposal',one);require(before==snap(runtime),'proposal route mutated runtime')
    finally:
        proc.terminate()
        try:proc.communicate(timeout=8)
        except subprocess.TimeoutExpired:proc.kill();proc.communicate(timeout=5)
def test_first_use_shell_exposes_preview_catalog_and_valid_javascript()->None:
    html=render_first_use_shell();
    for token in ('Conversational action portal','action-preview','action-tool-count','/api/conversation-action/catalog','/api/conversation-action/proposal','Nothing was saved, executed, or authorized'):require(token in html,token)
    script=re.search(r'<script>\s*(.*?)\s*</script>',html,re.S);require(script is not None,'script missing');tmp=Path(tempfile.mkdtemp(prefix='eidolon-v1104-js-'))/'shell.js';tmp.write_text(script.group(1),encoding='utf-8');run=subprocess.run(['node','--check',str(tmp)],capture_output=True,text=True,timeout=30);require(run.returncode==0,run.stderr)
def test_metadata_docs_and_focused_registration_align()->None:
    import release_metadata
    require(tuple(int(x) for x in release_metadata.WORKING_SOURCE_VERSION.split('.'))>=(1104,2),release_metadata.WORKING_SOURCE_VERSION)
    dashboard=(AGENT/'dashboard.py').read_text(encoding='utf-8');require('/api/conversation-action/catalog' in dashboard and '/api/conversation-action/proposal' in dashboard,dashboard[-500:])
    verifier=(ROOT/'tools/post_review_development_verify.py').read_text(encoding='utf-8')
    for name in ('tools/v1104_0_conversation_action_intent_classification_tests.py','tools/v1104_1_bounded_operator_visible_tool_catalog_tests.py','tools/v1104_2_action_proposal_explanation_cards_tests.py'):require(verifier.count(f'"{name}"')==1,name)
    roadmap=(ROOT/'archive/docs/legacy_dependencies/roadmaps/README_V1100_ROADMAP.md').read_text(encoding='utf-8');require(release_metadata.WORKING_SOURCE_VERSION in roadmap,'current roadmap version')
    require(f'## v{release_metadata.WORKING_SOURCE_VERSION}' in (ROOT/'README_RELEASE_HISTORY.md').read_text(encoding='utf-8'),'current history')
    for name in ('README.md','archive/docs/legacy_dependencies/roadmaps/README_DESKTOP_ALPHA.md','README_NEXT_STEPS.md'):require(release_metadata.WORKING_SOURCE_VERSION in (ROOT/name).read_text(encoding='utf-8'),name)
TESTS=[(n.removeprefix('test_'),f) for n,f in list(globals().items()) if n.startswith('test_')]
def main()->int:
    argparse.ArgumentParser().add_argument('--json',action='store_true');checks=[];passed=0
    for name,fn in TESTS:
        try:fn()
        except Exception as e:checks.append({'name':name,'status':'fail','message':f'{type(e).__name__}: {e}'})
        else:passed+=1;checks.append({'name':name,'status':'pass','message':''})
    report={'suite':'v1104.2-action-proposal-explanation-cards','ok':passed==len(TESTS),'passed':passed,'total':len(TESTS),'checks':checks};print(json.dumps(report,indent=2));return 0 if report['ok'] else 1
if __name__=='__main__':raise SystemExit(main())
