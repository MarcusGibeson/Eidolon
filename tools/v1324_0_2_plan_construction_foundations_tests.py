from __future__ import annotations
import json,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'conscious_agent'));sys.dont_write_bytecode=True
from plan_construction import *
from goal_representation import create_goal
checks=[]
def req(v,n):checks.append(n);assert v,n
g=create_goal(outcome='implement bounded feature',acceptance_criteria=['works'],stop_conditions=['unsafe side effect']);c={'goal_digest':g['goal_digest'],'approach_set_id':'a','workspace_digest':'w','source_manifest_digest':'m','selected_approach_id':'1','approaches':[{'approach_id':'1','approach_code':'routine_reversible_choice'}]}
with tempfile.TemporaryDirectory() as td:
 r=build_plan(g,c,runtime_root=td)['plan'];req(CONTRACT_VERSION=='v1324.8','contract');req(r['step_count']==4 and r['acyclic'],'default_plan');req(r['checkpoint_count']==4 and r['verification_step_count']==4 and r['rollback_step_count']==4,'verification_rollback');req(r['acceptance_criterion_count']==1 and r['stop_condition_count']==1,'criteria');req(r['execution_ready_structure'] and not r['execution_authorized'],'structured_not_authorized')
print(json.dumps({'suite':'v1324.0-2-plan-construction','ok':True,'passed':len(checks),'checks':checks},sort_keys=True))
