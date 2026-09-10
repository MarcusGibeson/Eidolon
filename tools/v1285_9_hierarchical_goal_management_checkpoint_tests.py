from __future__ import annotations
import json,os,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.dont_write_bytecode=True;os.environ['PYTHONDONTWRITEBYTECODE']='1';sys.path[:0]=[str(ROOT/'conscious_agent'),str(ROOT)]
from hierarchical_goal_management_checkpoint import build_hierarchical_goal_management_checkpoint
C=[]
def req(v,l):
 if not v:raise AssertionError(l)
 C.append(l)
r=build_hierarchical_goal_management_checkpoint(source_root=ROOT);req(r['ok'],'checkpoint');req(r['checkpoint_version']=='1285.9','version');req(all(r['checks'].values()),'checks');d=r['details'];req(d['next_bounded_unit']=='v1286 Dynamic Replanning','next');req(d['v1286_started'] is False,'unstarted');req(d['objective_decomposed_to_milestones_tasks_tests_recovery_completion'],'decomposition');req(d['original_operator_intent_preserved'],'intent');req(d['hierarchy_is_not_execution_authority'],'non_authorizing');req(not d['checkpoint_executes_provider'] and not d['checkpoint_executes_tests'] and not d['checkpoint_mutates_source'],'readonly');print(json.dumps({'ok':True,'suite':'v1285.9-hierarchical-goal-management-checkpoint','passed':len(C),'failed':0,'checks':C},sort_keys=True))
