from __future__ import annotations
import json,os,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.dont_write_bytecode=True;os.environ['PYTHONDONTWRITEBYTECODE']='1';sys.path.insert(0,str(ROOT/'conscious_agent'))
from competing_candidate_evaluation_checkpoint import competing_candidate_evaluation_checkpoint
C=[]
def req(v,l):
 if not v:raise AssertionError(l)
 C.append(l)
r=competing_candidate_evaluation_checkpoint(ROOT);req(r['ok'],'checkpoint');req(r['contract_version']=='v1294.9','version');req(all(r['checks'].values()),'checks');req(r['checks']['comparison_only_when_uncertainty_warrants'],'trigger');req(r['checks']['candidate_workspaces_isolated'] and r['checks']['verification_runs_independent'],'isolation');req(r['checks']['actual_disposable_competing_repairs_exercised'],'actual_repairs');req(r['checks']['correctness_quality_risk_cost_reversibility_uncertainty_compared'],'tradeoffs');req(r['checks']['all_candidates_can_be_rejected_or_ambiguous_result_deferred'],'reject_defer');req(r['checks']['selection_not_application_update_or_authority'],'boundary');req(r['checks']['native_windows_candidate_isolation_validation_pending'],'native');req(r['next']=='v1295 Comprehensive Verification' and r['v1295_started'] and r['checks']['v1295_transition_coherent'],'next_transition');req(r['read_only'] and not r['source_application_authorized'] and not r['release_authorized'],'readonly')
print(json.dumps({'ok':True,'suite':'v1294.9-competing-candidate-evaluation-checkpoint','passed':len(C),'failed':0,'checks':C},sort_keys=True))
