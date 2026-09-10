from __future__ import annotations
import json, os, subprocess, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
for p in (ROOT,ROOT/'conscious_agent',ROOT/'tools'):
    if str(p) not in sys.path: sys.path.insert(0,str(p))
from broader_project_language_adapters_checkpoint import build_broader_project_language_adapters_checkpoint
from checkpoint_registry import inspect_checkpoint_registry
from conscious_agent.api_server import handle_api_get, dispatch_api
checks=[]
def check(v): checks.append(bool(v))
report=build_broader_project_language_adapters_checkpoint(source_root=ROOT)
check(report.get('ok')); check(report.get('checkpoint_id')=='broader-project-language-adapters-checkpoint'); check(report.get('contract_version')=='v1238.9'); check(report.get('read_only') is True); check(report.get('source_signature_unchanged') is True); check(report.get('passed')==report.get('total'))
proc=subprocess.run([sys.executable,str(ROOT/'eidolon.py'),'broader-project-language-adapters-checkpoint'],cwd=ROOT,text=True,capture_output=True,timeout=120,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'})
check(proc.returncode==0)
try: data=json.loads(proc.stdout.strip().splitlines()[-1]); check(data.get('ok')); check(data.get('checkpoint_id')=='broader-project-language-adapters-checkpoint')
except Exception: check(False); check(False)
registry=inspect_checkpoint_registry(source_root=ROOT); row=next((x for x in registry.get('checkpoints',[]) if x.get('checkpoint_id')=='broader-project-language-adapters-checkpoint'),{})
check(bool(row)); check(row.get('contract_version')=='v1238.9'); check(row.get('read_only') is True); check(row.get('required_input_count')==0)
for route,checkpoint in [('broader-project-language-adapters-checkpoint',True),('broader-project-language-adapter-registry',False),('broader-project-language-adapter-assessments',False),('broader-project-language-adapter-reviews',False)]:
    code,payload=handle_api_get('/api/cognition/'+route); check(code==200); check(payload.get('ok')); data=payload.get('data') or {}; check(data.get('checkpoint_id')=='broader-project-language-adapters-checkpoint' if checkpoint else data.get('content_free') is True)
code,payload=dispatch_api('POST','/api/cognition/broader-project-language-adapter-registry',body={}); check(code in {404,405}); check(not payload.get('ok'))
print(json.dumps({'ok':all(checks),'passed':sum(checks),'total':len(checks),'checkpoint':{'external':report.get('passed'),'internal':report.get('total')}},sort_keys=True)); raise SystemExit(0 if all(checks) else 1)
