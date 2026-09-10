from __future__ import annotations
import json,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'conscious_agent'));sys.dont_write_bytecode=True
from evidence_dynamic_replanning import *
from project_evidence_store import atomic_json,evidence_root
checks=[]
def req(v,n):checks.append(n);assert v,n
plan={'plan_id':'p','goal_digest':'g','source_manifest_digest':'m','steps':[{'step_code':'a'},{'step_code':'b','depends_on':['a']}],'execution_authorized':False}
with tempfile.TemporaryDirectory() as td:
 try:replan_from_evidence(plan,completed_step_codes=['missing'],runtime_root=td);ok=False
 except ValueError:ok=True
 req(ok,'unknown_completed_rejected')
 try:replan_from_evidence({**plan,'execution_authorized':True},runtime_root=td);ok=False
 except ValueError:ok=True
 req(ok,'authority_plan_rejected')
 r=replan_from_evidence(plan,evidence_change={'evidence_digests':['e']},runtime_root=td)['dynamic_replanning'];raw=load_dynamic_replanning(r['replan_id'],runtime_root=td,include_private=True);raw['reason_code']='operator_revision';atomic_json(evidence_root('evidence_dynamic_replanning',td)/'records'/f"{r['replan_id']}.json",raw);req(load_dynamic_replanning(r['replan_id'],runtime_root=td)=={},'tamper_rejected')
 try:replan_from_evidence(plan,completed_step_codes=['a'],replacement_specs=[{'step_code':'a'}],runtime_root=td);ok=False
 except ValueError:ok=True
 req(ok,'replacement_completed_or_duplicate_rejected')
print(json.dumps({'suite':'v1327.6-8-dynamic-replanning','ok':True,'passed':len(checks),'checks':checks},sort_keys=True))
