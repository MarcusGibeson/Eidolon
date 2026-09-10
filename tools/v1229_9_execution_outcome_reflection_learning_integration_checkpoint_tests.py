from __future__ import annotations
import json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
for value in (ROOT/'conscious_agent',ROOT/'tools'):
    if str(value) not in sys.path:sys.path.insert(0,str(value))
from execution_outcome_reflection_learning_integration_checkpoint import build_execution_outcome_reflection_learning_integration_checkpoint
checks=[]
def check(v):checks.append(bool(v))
report=build_execution_outcome_reflection_learning_integration_checkpoint(source_root=ROOT)
for value in (report.get('ok'),report.get('read_only') is True,report.get('source_signature_unchanged') is True,report.get('runtime_data_read') is False,report.get('runtime_data_written') is False,report.get('authority_granted') is False,report.get('cognition_written') is False,report.get('passed')==report.get('total')):check(value)
proc=subprocess.run([sys.executable,str(ROOT/'eidolon.py'),'execution-outcome-reflection-learning-integration-checkpoint'],cwd=ROOT,text=True,capture_output=True,timeout=45)
check(proc.returncode==0)
try: cli=json.loads(proc.stdout.strip().splitlines()[-1]);check(cli.get('ok') is True);check(cli.get('checkpoint_id')=='execution-outcome-reflection-learning-integration-checkpoint')
except Exception: check(False);check(False)
from checkpoint_registry import inspect_checkpoint_registry
registry=inspect_checkpoint_registry(source_root=ROOT);row=next((x for x in registry['checkpoints'] if x['checkpoint_id']=='execution-outcome-reflection-learning-integration-checkpoint'),{})
check(row.get('contract_version')=='v1229.9');check(row.get('read_only') is True);check(row.get('required_input_count')==0)
print(json.dumps({'ok':all(checks),'passed':sum(checks),'total':len(checks),'internal_passed':report.get('passed'),'internal_total':report.get('total')},sort_keys=True));raise SystemExit(0 if all(checks) else 1)
