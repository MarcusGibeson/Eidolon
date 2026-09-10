from __future__ import annotations
import json,os,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.dont_write_bytecode=True;os.environ['PYTHONDONTWRITEBYTECODE']='1'
for p in (ROOT,ROOT/'conscious_agent',ROOT/'tools'):
 if str(p) not in sys.path:sys.path.insert(0,str(p))
from calibrated_uncertainty_checkpoint import build_calibrated_uncertainty_checkpoint
C=[]
def req(v,l):
 if not v:raise AssertionError(l)
 C.append(l)
r=build_calibrated_uncertainty_checkpoint(source_root=ROOT);req(r['ok'],'checkpoint');req(r['checkpoint_version']=='1282.9','version');req(all(r['checks'].values()),'checks');d=r['details'];req(d['next_bounded_unit']=='v1283 Development Memory Relevance','next');req(d['v1283_started'] is False,'unstarted');req(d['epistemic_states_preserved'] and d['confidence_changes_with_evidence'],'calibration');req(d['assumption_confidence_capped'] and d['unknown_not_treated_as_false'],'epistemic');req(d['duplicate_evidence_does_not_double_count'],'dedupe');req(not d['checkpoint_executes_provider'] and not d['checkpoint_executes_tests'] and not d['checkpoint_mutates_source'],'readonly')
print(json.dumps({'ok':True,'suite':'v1282.9-calibrated-uncertainty-checkpoint','passed':len(C),'failed':0,'checks':C},sort_keys=True))
