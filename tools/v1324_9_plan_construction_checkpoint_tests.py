from __future__ import annotations
import json,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'conscious_agent'));sys.dont_write_bytecode=True
from plan_construction import *
from goal_representation import create_goal
from release_authority import WORKING_SOURCE_VERSION,CHECKPOINT_HISTORY,NEXT_BOUNDED_UNIT
checks=[]
def req(v,n):checks.append(n);assert v,n
g=create_goal(outcome='x');c={'goal_digest':g['goal_digest'],'approach_set_id':'a','workspace_digest':'w','source_manifest_digest':'m','selected_approach_id':'1','approaches':[{'approach_id':'1','approach_code':'routine_reversible_choice'}]}
with tempfile.TemporaryDirectory() as td:r=build_plan(g,c,runtime_root=td)['plan'];req(r['acyclic'] and r['step_count']>=1,'checkpoint');req(not r['execution_authorized'] and not r['project_mutation_authorized'],'governance')
req(tuple(int(x) for x in WORKING_SOURCE_VERSION.split('.'))>=(1324,9),'metadata');req(any(v=='1324.9' for v,_ in CHECKPOINT_HISTORY),'history');req((WORKING_SOURCE_VERSION!='1324.9') or ('v1325' in NEXT_BOUNDED_UNIT),'historical_next_exact_when_current')
print(json.dumps({'suite':'v1324.9-plan-construction-checkpoint','ok':True,'passed':len(checks),'checks':checks},sort_keys=True))
