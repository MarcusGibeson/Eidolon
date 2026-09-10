from __future__ import annotations
import json, os, subprocess, sys, tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
for p in (ROOT,ROOT/'conscious_agent',ROOT/'tools'):
    if str(p) not in sys.path: sys.path.insert(0,str(p))
os.environ.setdefault('EIDOLON_DATA_DIR',tempfile.mkdtemp(prefix='eidolon-v1237-checkpoint-api-'))
from multi_tool_orchestration_checkpoint import build_multi_tool_orchestration_checkpoint
from checkpoint_registry import inspect_checkpoint_registry
from conscious_agent.api_server import handle_api_get
checks=[]
def check(v): checks.append(bool(v))
report=build_multi_tool_orchestration_checkpoint(source_root=ROOT)
for v in (
    report.get('ok'),report.get('checkpoint_id')=='multi-tool-orchestration-checkpoint',report.get('contract_version')=='v1237.9',
    report.get('retained_contract_version')=='v1237.8',report.get('milestone_name')=='Multi-Tool Orchestration',
    report.get('roadmap_path')=='Balanced Mind-and-Action Path 3',report.get('read_only') is True,report.get('content_free') is True,
    report.get('project_scoped') is True,report.get('source_signature_unchanged') is True,
    report.get('source_file_count_before')==report.get('source_file_count_after'),report.get('runtime_data_read') is False,
    report.get('runtime_data_written') is False,report.get('provider_contacted') is False,report.get('commands_executed') is False,
    report.get('tests_executed') is False,report.get('project_modified') is False,report.get('queue_modified') is False,
    report.get('schedule_modified') is False,report.get('cognition_written') is False,report.get('source_modified') is False,
    report.get('authority_granted') is False,report.get('tool_invocation_authorized') is False,
    report.get('automatic_continuation_authorized') is False,report.get('automatic_retry_authorized') is False,
    report.get('launch_authorized') is False,report.get('resume_authorized') is False,report.get('old_authority_reusable') is False,
    report.get('passed')==report.get('total'),
): check(v)
proc=subprocess.run([sys.executable,str(ROOT/'eidolon.py'),'multi-tool-orchestration-checkpoint'],cwd=ROOT,text=True,capture_output=True,timeout=120,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'})
check(proc.returncode==0)
try: data=json.loads(proc.stdout.strip().splitlines()[-1]); check(data.get('ok')); check(data.get('checkpoint_id')=='multi-tool-orchestration-checkpoint')
except Exception: check(False); check(False)
registry=inspect_checkpoint_registry(source_root=ROOT); row=next((x for x in registry.get('checkpoints',[]) if x.get('checkpoint_id')=='multi-tool-orchestration-checkpoint'),{})
check(row.get('contract_version')=='v1237.9'); check(row.get('read_only') is True); check(row.get('required_input_count')==0)
for route,checkpoint in (
    ('/api/cognition/multi-tool-orchestration-checkpoint',True),('/api/cognition/multi-tool-orchestration-plans',False),
    ('/api/cognition/multi-tool-orchestration-reviews',False),('/api/cognition/multi-tool-orchestration-results',False),
    ('/api/cognition/multi-tool-orchestration-handoffs',False),('/api/cognition/multi-tool-orchestration-handoff-reviews',False),
):
    status,payload=handle_api_get(route); check(status==200); check(payload.get('ok') is True)
    data=payload.get('data') or {}; check(data.get('checkpoint_id')=='multi-tool-orchestration-checkpoint' if checkpoint else data.get('content_free') is True)
print(json.dumps({'ok':all(checks),'passed':sum(checks),'total':len(checks),'internal_passed':report.get('passed'),'internal_total':report.get('total')},sort_keys=True)); raise SystemExit(0 if all(checks) else 1)
