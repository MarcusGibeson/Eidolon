from __future__ import annotations
import json,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'conscious_agent'));sys.dont_write_bytecode=True
from plan_quality_scoring import score_plan_quality
from ordinary_chat_development_campaign import process_ordinary_chat_development_turn
checks=[]
def req(v,n):checks.append(n);assert v,n
plan={'plan_id':'p','goal_digest':'g','source_manifest_digest':'m','steps':[{'step_code':'a'},{'step_code':'b'},{'step_code':'c'}],'acceptance_criterion_count':1,'execution_authorized':False}
out={'outcome_observed':True,'verification_evidence_digests':['v1','v2'],'prediction_total':2,'prediction_hits':2,'rework_step_count':1,'unnecessary_step_count':1,'missed_dependency_count':0,'acceptance_criteria_total':1,'acceptance_criteria_met_count':1}
with tempfile.TemporaryDirectory() as td:
 r=score_plan_quality(plan,out,runtime_root=td)['plan_quality'];req(r['metrics']['prediction_accuracy']==100 and r['metrics']['acceptance_coverage']==100,'grounded_metrics');req(r['metrics']['rework_efficiency']<100,'rework_visible')
 chat=process_ordinary_chat_development_turn('score plan quality',project_state={'constructed_plan':plan,'plan_outcome_evidence':out},runtime_root=td);req(chat.get('active') and chat['plan_quality']['evaluable'],'ordinary_route');req(not chat.get('planning_execution_authorized'),'no_authority')
print(json.dumps({'suite':'v1329.3-5-plan-quality-scoring','ok':True,'passed':len(checks),'checks':checks},sort_keys=True))
