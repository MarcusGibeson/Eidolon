from __future__ import annotations
import json,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'conscious_agent'));sys.dont_write_bytecode=True
from plan_critique import *
from release_authority import WORKING_SOURCE_VERSION,CHECKPOINT_HISTORY,NEXT_BOUNDED_UNIT
checks=[]
def req(v,n):checks.append(n);assert v,n
plan={'plan_id':'p','goal_digest':'g','source_manifest_digest':'m','steps':[{'step_code':'inspect_scope'}],'checkpoint_count':1,'verification_step_count':1,'rollback_step_count':1,'execution_authorized':False}
with tempfile.TemporaryDirectory() as td:r=critique_plan(plan,runtime_root=td)['plan_critique'];req(r['finding_count']>=0,'checkpoint');req(not r['planning_execution_authorized'] and not r['critique_mutated_plan'],'governance')
req(tuple(int(x) for x in WORKING_SOURCE_VERSION.split('.'))>=(1325,9),'metadata');req(any(v=='1325.9' for v,_ in CHECKPOINT_HISTORY),'history');req((WORKING_SOURCE_VERSION!='1325.9') or ('v1326' in NEXT_BOUNDED_UNIT),'historical_next_exact_when_current')
print(json.dumps({'suite':'v1325.9-plan-critique-checkpoint','ok':True,'passed':len(checks),'checks':checks},sort_keys=True))
