from __future__ import annotations
import json,os,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.dont_write_bytecode=True;os.environ['PYTHONDONTWRITEBYTECODE']='1';sys.path[:0]=[str(ROOT/'conscious_agent'),str(ROOT)]
from dynamic_replanning_checkpoint import build_dynamic_replanning_checkpoint
C=[]
def req(v,l):
 if not v:raise AssertionError(l)
 C.append(l)
r=build_dynamic_replanning_checkpoint(source_root=ROOT);req(r['ok'],'checkpoint');req(r['checkpoint_version']=='1286.9','version');req(all(r['checks'].values()),'checks');d=r['details'];req(d['next_bounded_unit']=='v1287 Unified Conversation and Action','next');req(d['v1287_started'] is False,'unstarted');req(d['handles_interruptions_new_requirements_failed_assumptions_new_evidence_priority_changes'],'events');req(d['preserves_valid_completed_work'] and d['suppresses_failed_strategy_repeat'],'preservation');req(d['original_operator_intent_preserved'],'intent');req(not d['checkpoint_executes_provider'] and not d['checkpoint_executes_tests'] and not d['checkpoint_mutates_source'],'readonly');print(json.dumps({'ok':True,'suite':'v1286.9-dynamic-replanning-checkpoint','passed':len(C),'failed':0,'checks':C},sort_keys=True))
