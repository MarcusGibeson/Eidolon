from __future__ import annotations
import json,os,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.dont_write_bytecode=True;os.environ['PYTHONDONTWRITEBYTECODE']='1';sys.path[:0]=[str(ROOT/'conscious_agent'),str(ROOT)]
from experiential_learning_checkpoint import build_experiential_learning_checkpoint
C=[]
def req(v,l):
 if not v:raise AssertionError(l)
 C.append(l)
r=build_experiential_learning_checkpoint(source_root=ROOT);req(r['ok'],'checkpoint');req(r['checkpoint_version']=='1284.9','version');req(all(r['checks'].values()),'checks');d=r['details'];req(d['next_bounded_unit']=='v1285 Hierarchical Goal Management','next');req(d['v1285_started'] is False,'unstarted');req(d['verified_outcomes_only'],'verified');req(d['stale_contradicted_context_inappropriate_lessons_suppressed'],'suppression');req(d['lessons_not_permanent_rules'],'not_permanent');req(not d['checkpoint_executes_provider'] and not d['checkpoint_executes_tests'] and not d['checkpoint_mutates_source'],'readonly');print(json.dumps({'ok':True,'suite':'v1284.9-experiential-learning-checkpoint','passed':len(C),'failed':0,'checks':C},sort_keys=True))
