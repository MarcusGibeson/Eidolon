from __future__ import annotations
import json,os,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.dont_write_bytecode=True;os.environ['PYTHONDONTWRITEBYTECODE']='1';sys.path.insert(0,str(ROOT/'conscious_agent'))
from supervised_autonomy_rehearsal_checkpoint import supervised_autonomy_rehearsal_checkpoint
checks=[]
def req(v,n):checks.append(n);assert v,n
r=supervised_autonomy_rehearsal_checkpoint(ROOT);req(r['ok'],'checkpoint');req(r['contract_version']=='v1299.9','version');req(r['status']=='final_supervised_autonomy_rehearsal_checkpoint_ready','status');req(all(r['checks'].values()),'checks');req(r['checks']['real_multifile_integrity_defect_repaired'],'real_defect');req(r['checks']['proposal_deliberation_campaign_candidate_verification_lineage_reused'],'lineage');req(r['checks']['operator_inspect_defer_reject_cancel_controls_preserved'],'controls');req(r['checks']['rollback_remains_separately_governed'],'rollback_boundary');req(r['checks']['exact_v1269_update_authorization_remains_required'],'update_boundary');req(r['checks']['generic_authorization_remains_insufficient'],'generic_boundary');req(r['checks']['native_windows_rehearsal_pending'],'native_pending');req(r['next']=='v1300 Supervised Self-Development Beta' and r['v1300_started'] and r['checks']['v1300_transition_coherent'],'next_transition');req(r['read_only'] and not r['source_mutation_authorized'] and not r['release_authorized'],'readonly')
print(json.dumps({'suite':'v1299.9-supervised-autonomy-rehearsal-checkpoint','ok':True,'passed':len(checks),'failed':0,'checks':checks},sort_keys=True))
