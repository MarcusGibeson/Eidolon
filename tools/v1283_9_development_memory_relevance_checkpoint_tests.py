from __future__ import annotations
import json,os,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.dont_write_bytecode=True;os.environ['PYTHONDONTWRITEBYTECODE']='1';sys.path[:0]=[str(ROOT/'conscious_agent'),str(ROOT)]
from development_memory_relevance_checkpoint import build_development_memory_relevance_checkpoint
C=[]
def req(v,l):
 if not v:raise AssertionError(l)
 C.append(l)
r=build_development_memory_relevance_checkpoint(source_root=ROOT);req(r['ok'],'checkpoint');req(r['checkpoint_version']=='1283.9','version');req(all(r['checks'].values()),'checks');d=r['details'];req(d['next_bounded_unit']=='v1284 Experiential Learning','next');req(d['v1284_started'] is False,'unstarted');req(d['retrieves_requirements_failures_decisions_preferences_approaches_lessons'],'types');req(d['weak_relevance_can_return_empty'] and not d['indiscriminate_memory_dump'],'relevance');req(not d['checkpoint_executes_provider'] and not d['checkpoint_executes_tests'] and not d['checkpoint_mutates_source'],'readonly');print(json.dumps({'ok':True,'suite':'v1283.9-development-memory-relevance-checkpoint','passed':len(C),'failed':0,'checks':C},sort_keys=True))
