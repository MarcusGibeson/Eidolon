from __future__ import annotations
import json,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'conscious_agent'));sys.dont_write_bytecode=True
from risk_sensitive_planning import *
checks=[]
def req(v,n):checks.append(n);assert v,n
plan={'plan_id':'p','goal_digest':'g','source_manifest_digest':'m','steps':[{'step_code':'x','mutation_expected':True}],'execution_authorized':False}
with tempfile.TemporaryDirectory() as td:
 r=assess_plan_risk(plan,impact_analysis={'analysis_id':'i','protected_authority_surface_predicted':True},runtime_root=td)['risk_sensitive_planning'];req(r['risk_tier']=='critical' and not r['planning_progress_allowed'],'protected_critical');req(r['approval_requirement']=='separate_protected_action_approval_required','protected_approval_requirement')
 loaded=load_risk_sensitive_planning(r['assessment_id'],runtime_root=td,include_private=True);loaded['risk_tier']='low';from project_evidence_store import atomic_json,evidence_root;atomic_json(evidence_root('risk_sensitive_planning',td)/'records'/f"{r['assessment_id']}.json",loaded);req(load_risk_sensitive_planning(r['assessment_id'],runtime_root=td)=={},'tamper_rejected')
 try: assess_plan_risk({**plan,'execution_authorized':True},runtime_root=td);ok=False
 except ValueError: ok=True
 req(ok,'authority_plan_rejected')
print(json.dumps({'suite':'v1326.6-8-risk-sensitive-planning','ok':True,'passed':len(checks),'checks':checks},sort_keys=True))
