from __future__ import annotations
import json,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'conscious_agent'));sys.dont_write_bytecode=True
from plan_critique import *
checks=[]
def req(v,n):checks.append(n);assert v,n
plan={'plan_id':'p','goal_digest':'g','source_manifest_digest':'m','steps':[{'step_code':'inspect_scope'},{'step_code':'implement_change','mutation_expected':True},{'step_code':'focused_verification'},{'step_code':'acceptance_review'}],'checkpoint_count':4,'verification_step_count':4,'rollback_step_count':4,'acceptance_criterion_count':1,'execution_authorized':False,'project_mutation_authorized':False,'standing_authority_granted':False}
with tempfile.TemporaryDirectory() as td:
 r=critique_plan(plan,goal={'goal_digest':'g','acceptance_criteria_digests':['a']},runtime_root=td)['plan_critique'];req(CONTRACT_VERSION=='v1325.8','contract');req(tuple(CATEGORIES)==('missing_requirements','hidden_coupling','unsafe_authority','weak_verification'),'categories');req(r['blocking_count']==0 and r['plan_acceptable_for_next_planning_stage'],'clear');req(not r['critique_mutated_plan'],'separate');req(not r['action_executed'],'nonexecuting')
print(json.dumps({'suite':'v1325.0-2-plan-critique','ok':True,'passed':len(checks),'checks':checks},sort_keys=True))
