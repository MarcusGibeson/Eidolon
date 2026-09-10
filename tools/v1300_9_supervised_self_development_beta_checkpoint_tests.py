from __future__ import annotations
import json,os,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.dont_write_bytecode=True;os.environ['PYTHONDONTWRITEBYTECODE']='1';sys.path.insert(0,str(ROOT/'conscious_agent'))
from supervised_self_development_beta_checkpoint import supervised_self_development_beta_checkpoint
checks=[]
def req(v,n):checks.append(n);assert v,n
r=supervised_self_development_beta_checkpoint(ROOT);req(r['ok'],'checkpoint');req(r['contract_version']=='v1300.9','version');req(r['status']=='supervised_self_development_beta_checkpoint_ready','status');req(all(r['checks'].values()),'checks');req(r['checks']['inspection_proposal_deliberation_planning_lineage'],'front_half');req(r['checks']['competing_candidate_and_isolated_build_lineage'],'candidate_lineage');req(r['checks']['verification_diagnosis_repair_reverification_lineage'],'repair_lineage');req(r['checks']['operator_review_and_exact_update_lineage'],'update_lineage');req(r['checks']['disposable_exact_update_integration_required'],'disposable_update');req(r['checks']['automatic_recovery_integration_required'],'recovery');req(r['checks']['generic_authorization_insufficient'],'generic_boundary');req(r['checks']['successful_operator_rollback_separately_governed'],'rollback_boundary');req(r['checks']['native_windows_beta_validation_pending'],'native_pending');req(r['checks']['roadmap_complete_through_v1300'],'roadmap_complete');req(r['next']=='Post-v1300 Desktop Codex and Native Windows Validation Gate','next');req(r['read_only'] and not r['self_update_authorized'] and not r['release_authorized'],'readonly')
print(json.dumps({'suite':'v1300.9-supervised-self-development-beta-checkpoint','ok':True,'passed':len(checks),'failed':0,'checks':checks},sort_keys=True))
