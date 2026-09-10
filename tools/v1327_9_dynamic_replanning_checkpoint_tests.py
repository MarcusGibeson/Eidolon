from __future__ import annotations
import json,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'conscious_agent'));sys.dont_write_bytecode=True
from evidence_dynamic_replanning import *
from release_authority import WORKING_SOURCE_VERSION,CHECKPOINT_HISTORY,NEXT_BOUNDED_UNIT
checks=[]
def req(v,n):checks.append(n);assert v,n
plan={'plan_id':'p','goal_digest':'g','source_manifest_digest':'m','steps':[{'step_code':'a'},{'step_code':'b'}],'execution_authorized':False}
with tempfile.TemporaryDirectory() as td:r=replan_from_evidence(plan,completed_step_codes=['a'],evidence_change={'evidence_digests':['e']},runtime_root=td)['dynamic_replanning'];req(r['completed_step_count']==1 and not r['completed_work_repeated'],'checkpoint');req(not r['planning_execution_authorized'],'governance')
req(tuple(int(x) for x in WORKING_SOURCE_VERSION.split('.'))>=(1327,9),'metadata');req(any(v=='1327.9' for v,_ in CHECKPOINT_HISTORY),'history');req((WORKING_SOURCE_VERSION!='1327.9') or ('v1328' in NEXT_BOUNDED_UNIT),'historical_next_exact_when_current')
print(json.dumps({'suite':'v1327.9-dynamic-replanning-checkpoint','ok':True,'passed':len(checks),'checks':checks},sort_keys=True))
