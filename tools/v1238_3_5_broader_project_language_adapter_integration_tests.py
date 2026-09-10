from __future__ import annotations
import json, os, subprocess, sys, tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
for p in (ROOT,ROOT/'conscious_agent',ROOT/'tools'):
    if str(p) not in sys.path: sys.path.insert(0,str(p))
import broader_project_language_adapters as a
from ordinary_chat_development_campaign import process_ordinary_chat_development_turn
from conscious_agent.api_server import handle_api_get, dispatch_api
checks=[]
def check(v): checks.append(bool(v))
rt=tempfile.mkdtemp(prefix='eidolon-v1238-integration-')
assessment=a.prepare_broader_project_adapter_assessment('project_'+'d'*16,relative_paths=['pom.xml','src/main/java/App.java','src/test/java/AppTest.java'],manifest_digests={'pom.xml':'1'*64},runtime_root=rt)
check(assessment.get('ok')); check(assessment.get('selected_adapter_id')=='java_maven')
phrase=f"review broader project adapter accept_adapter for assessment {assessment['assessment_id']} digest {assessment['assessment_digest']}"
turn=process_ordinary_chat_development_turn(phrase,runtime_root=rt)
row=turn.get('broader_project_language_adapter') or {}
check(turn.get('active')); check(row.get('ok')); check(row.get('disposition')=='accept_adapter'); check(row.get('command_execution_authorized') is False); check(row.get('test_execution_authorized') is False)
replay=process_ordinary_chat_development_turn(phrase,runtime_root=rt).get('broader_project_language_adapter') or {}
check(replay.get('review_id')==row.get('review_id')); check(replay.get('review_digest')==row.get('review_digest'))
for text,key in [('show broader project adapter assessments','assessments'),('show broader project adapter reviews','reviews'),('show broader project adapter registry','adapters'),(f"show broader project adapter assessment {assessment['assessment_id']}",'assessment')]:
    out=process_ordinary_chat_development_turn(text,runtime_root=rt)
    check(out.get('active')); check((out.get('broader_project_language_adapter') or {}).get('ok'))
blue=a.prepare_adapter_orchestration_blueprint(assessment['assessment_id'],expected_assessment_digest=assessment['assessment_digest'],review_id=row['review_id'],expected_review_digest=row['review_digest'],runtime_root=rt)
check(blue.get('ok')); check(blue.get('status')=='broader_project_adapter_orchestration_blueprint_ready'); check(len(blue.get('tools') or [])==3); check(len(blue.get('steps') or [])==3); check(blue.get('fresh_separate_v1237_plan_review_required') is True); check(blue.get('tool_invocation_authorized') is False); check(blue.get('command_execution_authorized') is False)
# CLI read-only surfaces
for command,key in [('broader-project-language-adapter-registry','adapter_count'),('broader-project-language-adapter-assessments','assessment_count'),('broader-project-language-adapter-reviews','review_count')]:
    args=[sys.executable,str(ROOT/'eidolon.py'),command]
    if command!='broader-project-language-adapter-registry': args += ['--runtime-root',rt]
    proc=subprocess.run(args,cwd=ROOT,text=True,capture_output=True,timeout=90,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'})
    check(proc.returncode==0)
    try: data=json.loads(proc.stdout.strip().splitlines()[-1]); check(data.get('ok')); check(key in data)
    except Exception: check(False); check(False)
# GET only API
for route in ('broader-project-language-adapter-registry','broader-project-language-adapter-assessments','broader-project-language-adapter-reviews'):
    code,payload=handle_api_get('/api/cognition/'+route); check(code==200); check(payload.get('ok')); check((payload.get('data') or {}).get('content_free') is True)
code,payload=dispatch_api('POST','/api/cognition/broader-project-language-adapter-assessments',body={}); check(code in {404,405}); check(not payload.get('ok'))
# Non-exact casual text remains inert.
for text in ('It would be nice to support Java someday.','Maybe use Maven.','"review broader project adapter accept_adapter"'):
    out=a.process_broader_project_language_adapter_control(text,runtime_root=rt); check(out.get('active') is False)
print(json.dumps({'ok':all(checks),'passed':sum(checks),'total':len(checks)},sort_keys=True)); raise SystemExit(0 if all(checks) else 1)
