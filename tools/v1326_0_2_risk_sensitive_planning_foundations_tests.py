from __future__ import annotations
import json,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'conscious_agent'));sys.dont_write_bytecode=True
from risk_sensitive_planning import *
checks=[]
def req(v,n):checks.append(n);assert v,n
plan={'plan_id':'p','goal_digest':'g','source_manifest_digest':'m','steps':[{'step_code':'inspect_scope','mutation_expected':False},{'step_code':'implement_change','mutation_expected':True}], 'execution_authorized':False,'project_mutation_authorized':False}
with tempfile.TemporaryDirectory() as td:
 r=assess_plan_risk(plan,runtime_root=td)['risk_sensitive_planning'];req(CONTRACT_VERSION=='v1326.8','contract');req(r['risk_tier']=='low','low');req(r['required_isolation']=='candidate_workspace','isolation');req(r['requirements_are_not_grants'] and not r['approval_granted'],'requirements_not_grants');req(not r['planning_execution_authorized'] and not r['action_executed'],'nonexecuting')
print(json.dumps({'suite':'v1326.0-2-risk-sensitive-planning','ok':True,'passed':len(checks),'checks':checks},sort_keys=True))
