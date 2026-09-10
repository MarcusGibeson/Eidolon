from __future__ import annotations
import json, os, subprocess, sys, tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
for value in (ROOT,ROOT/'conscious_agent',ROOT/'tools'):
    if str(value) not in sys.path: sys.path.insert(0,str(value))
from mindful_execution_alpha_integration_benchmark_checkpoint import build_mindful_execution_alpha_integration_benchmark_checkpoint
from checkpoint_registry import inspect_checkpoint_registry
os.environ.setdefault("EIDOLON_DATA_DIR", tempfile.mkdtemp(prefix="eidolon-v1230-api-"))
from conscious_agent.api_server import handle_api_get
checks=[]
def check(v): checks.append(bool(v))
report=build_mindful_execution_alpha_integration_benchmark_checkpoint(source_root=ROOT)
for value in (
    report.get('ok'), report.get('checkpoint_id')=='mindful-execution-alpha-integration-benchmark-checkpoint',
    report.get('contract_version')=='v1230.9', report.get('milestone_name')=='Mindful Execution Alpha',
    report.get('roadmap_path')=='Balanced Mind-and-Action Path 3', report.get('read_only') is True,
    report.get('content_free') is True, report.get('source_signature_unchanged') is True,
    report.get('source_file_count_before')==report.get('source_file_count_after'), report.get('runtime_data_read') is False,
    report.get('runtime_data_written') is False, report.get('provider_contacted') is False,
    report.get('commands_executed') is False, report.get('tests_executed') is False,
    report.get('project_modified') is False, report.get('source_modified') is False,
    report.get('cognition_written') is False, report.get('authority_granted') is False,
    report.get('release_authorized') is False, report.get('passed')==report.get('total'),
): check(value)
proc=subprocess.run([sys.executable,str(ROOT/'eidolon.py'),'mindful-execution-alpha-integration-benchmark-checkpoint'],cwd=ROOT,text=True,capture_output=True,timeout=120)
check(proc.returncode==0)
try:
    cli=json.loads(proc.stdout.strip().splitlines()[-1]); check(cli.get('ok') is True); check(cli.get('checkpoint_id')=='mindful-execution-alpha-integration-benchmark-checkpoint')
except Exception: check(False); check(False)
registry=inspect_checkpoint_registry(source_root=ROOT); row=next((x for x in registry['checkpoints'] if x['checkpoint_id']=='mindful-execution-alpha-integration-benchmark-checkpoint'),{})
check(row.get('contract_version')=='v1230.9'); check(row.get('read_only') is True); check(row.get('required_input_count')==0)
status,payload=handle_api_get('/api/cognition/mindful-execution-alpha-integration-benchmark-checkpoint')
check(status==200); check(payload.get('ok') is True); check((payload.get('data') or {}).get('checkpoint_id')=='mindful-execution-alpha-integration-benchmark-checkpoint')
print(json.dumps({'ok':all(checks),'passed':sum(checks),'total':len(checks),'internal_passed':report.get('passed'),'internal_total':report.get('total')},sort_keys=True))
raise SystemExit(0 if all(checks) else 1)
