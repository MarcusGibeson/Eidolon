from __future__ import annotations
import json,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'conscious_agent'));sys.dont_write_bytecode=True
from evidence_dynamic_replanning import *
checks=[]
def req(v,n):checks.append(n);assert v,n
plan={'plan_id':'p','goal_digest':'g','source_manifest_digest':'m1','steps':[{'step_code':'inspect_scope','depends_on':[],'executed':False},{'step_code':'implement_change','depends_on':['inspect_scope'],'mutation_expected':True},{'step_code':'focused_verification','depends_on':['implement_change']}],'execution_authorized':False}
with tempfile.TemporaryDirectory() as td:
 r=replan_from_evidence(plan,completed_step_codes=['inspect_scope'],evidence_change={'evidence_digests':['e1'],'current_source_manifest_digest':'m2'},reason_code='source_change',runtime_root=td)['dynamic_replanning'];req(CONTRACT_VERSION=='v1327.8','contract');req(r['completed_step_codes']==['inspect_scope'],'completed_preserved');req(r['source_manifest_changed'] and r['route_changed'],'changed');req('inspect_scope' not in [x['step_code'] for x in r['revised_pending_steps']],'no_repeat');req(not r['previous_plan_mutated'] and not r['action_executed'],'nonexecuting')
print(json.dumps({'suite':'v1327.0-2-dynamic-replanning','ok':True,'passed':len(checks),'checks':checks},sort_keys=True))
