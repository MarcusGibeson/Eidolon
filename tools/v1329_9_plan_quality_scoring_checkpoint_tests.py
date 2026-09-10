from __future__ import annotations
import json,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'conscious_agent'));sys.dont_write_bytecode=True
from plan_quality_scoring import *
from release_authority import WORKING_SOURCE_VERSION,CHECKPOINT_HISTORY,NEXT_BOUNDED_UNIT
checks=[]
def req(v,n):checks.append(n);assert v,n
plan={'plan_id':'p','goal_digest':'g','source_manifest_digest':'m','steps':[{'step_code':'a'}],'execution_authorized':False}
with tempfile.TemporaryDirectory() as td:r=score_plan_quality(plan,runtime_root=td)['plan_quality'];req(not r['evaluable'],'checkpoint');req(r['score_is_outcome_evidence_not_authority'] and not r['planning_execution_authorized'],'governance')
req(tuple(int(x) for x in WORKING_SOURCE_VERSION.split('.'))>=(1329,9),'metadata');req(any(v=='1329.9' for v,_ in CHECKPOINT_HISTORY),'history');req((WORKING_SOURCE_VERSION!='1329.9') or ('v1330' in NEXT_BOUNDED_UNIT),'historical_next_exact_when_current')
print(json.dumps({'suite':'v1329.9-plan-quality-scoring-checkpoint','ok':True,'passed':len(checks),'checks':checks},sort_keys=True))
