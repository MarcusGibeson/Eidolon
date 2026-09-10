from __future__ import annotations
import json,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'conscious_agent'));sys.dont_write_bytecode=True
from plan_quality_scoring import *
checks=[]
def req(v,n):checks.append(n);assert v,n
plan={'plan_id':'p','goal_digest':'g','source_manifest_digest':'m','steps':[{'step_code':'a'},{'step_code':'b'}],'acceptance_criterion_count':2,'execution_authorized':False}
with tempfile.TemporaryDirectory() as td:
 r=score_plan_quality(plan,runtime_root=td)['plan_quality'];req(CONTRACT_VERSION=='v1329.8','contract');req(not r['evaluable'] and r['overall_score'] is None,'no_evidence_no_score');req(r['self_asserted_score_rejected'],'self_assertion_rejected')
 q=score_plan_quality(plan,{'outcome_observed':True,'verification_evidence_digests':['e'],'prediction_total':4,'prediction_hits':3,'rework_step_count':0,'unnecessary_step_count':0,'missed_dependency_count':0,'acceptance_criteria_total':2,'acceptance_criteria_met_count':2},runtime_root=td)['plan_quality'];req(q['evaluable'] and 0<=q['overall_score']<=100,'scored');req(set(q['metrics'])==set(METRICS),'metrics')
print(json.dumps({'suite':'v1329.0-2-plan-quality-scoring','ok':True,'passed':len(checks),'checks':checks},sort_keys=True))
