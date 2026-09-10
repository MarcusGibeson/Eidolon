from __future__ import annotations
import json,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'conscious_agent'));sys.dont_write_bytecode=True
from risk_sensitive_planning import *
from release_authority import WORKING_SOURCE_VERSION,CHECKPOINT_HISTORY,NEXT_BOUNDED_UNIT
checks=[]
def req(v,n):checks.append(n);assert v,n
plan={'plan_id':'p','goal_digest':'g','source_manifest_digest':'m','steps':[{'step_code':'x','mutation_expected':False}],'execution_authorized':False}
with tempfile.TemporaryDirectory() as td:r=assess_plan_risk(plan,runtime_root=td)['risk_sensitive_planning'];req(r['risk_tier']=='low','checkpoint');req(r['requirements_are_not_grants'] and not r['planning_execution_authorized'],'governance')
req(tuple(int(x) for x in WORKING_SOURCE_VERSION.split('.'))>=(1326,9),'metadata');req(any(v=='1326.9' for v,_ in CHECKPOINT_HISTORY),'history');req((WORKING_SOURCE_VERSION!='1326.9') or ('v1327' in NEXT_BOUNDED_UNIT),'historical_next_exact_when_current')
print(json.dumps({'suite':'v1326.9-risk-sensitive-planning-checkpoint','ok':True,'passed':len(checks),'checks':checks},sort_keys=True))
