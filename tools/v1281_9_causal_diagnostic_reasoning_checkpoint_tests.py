from __future__ import annotations
import json,os,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.dont_write_bytecode=True;os.environ['PYTHONDONTWRITEBYTECODE']='1'
for p in (ROOT,ROOT/'conscious_agent',ROOT/'tools'):
 if str(p) not in sys.path:sys.path.insert(0,str(p))
from causal_diagnostic_reasoning_checkpoint import build_causal_diagnostic_reasoning_checkpoint
C=[]
def req(v,l):
 if not v:raise AssertionError(l)
 C.append(l)
r=build_causal_diagnostic_reasoning_checkpoint(source_root=ROOT);req(r['ok'],'checkpoint');req(r['checkpoint_version']=='1281.9','version');req(all(r['checks'].values()),'checks');d=r['details'];req(d['next_bounded_unit']=='v1282 Calibrated Uncertainty','next');req(d['v1282_started'] is False,'unstarted');req(d['symptom_cause_distinction_present'] and d['discriminating_falsification_probe_required'],'causal');req(d['single_supporting_probe_does_not_prove_root_cause'],'no_overclaim');req(not d['checkpoint_executes_diagnostics'] and not d['checkpoint_executes_provider'] and not d['checkpoint_executes_tests'] and not d['checkpoint_mutates_source'],'readonly')
print(json.dumps({'ok':True,'suite':'v1281.9-causal-diagnostic-reasoning-checkpoint','passed':len(C),'failed':0,'checks':C},sort_keys=True))
