from __future__ import annotations
import json,os,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.dont_write_bytecode=True;os.environ['PYTHONDONTWRITEBYTECODE']='1';sys.path.insert(0,str(ROOT/'conscious_agent'))
from bounded_development_campaigns_checkpoint import bounded_development_campaigns_checkpoint
C=[]
def req(v,l):
 if not v:raise AssertionError(l)
 C.append(l)
r=bounded_development_campaigns_checkpoint(ROOT);req(r['ok'],'checkpoint');req(r['contract_version']=='v1293.9','version');req(all(r['checks'].values()),'checks');req(r['checks']['selected_improvement_identity_and_scope_sealed'],'identity_scope');req(r['checks']['pause_resume_cancel_and_recovery_bounded'],'resumable');req(r['checks']['scope_expansion_requires_separate_confirmation'],'scope');req(r['checks']['failed_strategy_history_prevents_silent_repeat'],'failed_strategy');req(r['checks']['completion_requires_full_evidence_chain'],'completion');req(r['checks']['campaign_progress_not_execution_or_update_authority'],'authority');req(r['checks']['native_windows_restart_and_multiprocess_validation_pending'],'native');req(r['next']=='v1294 Competing Candidate Evaluation' and r['v1294_started'] and r['checks']['v1294_transition_coherent'],'next_transition');req(r['read_only'] and not r['release_authorized'] and not r['project_mutation_authorized'],'readonly')
print(json.dumps({'ok':True,'suite':'v1293.9-bounded-development-campaigns-checkpoint','passed':len(C),'failed':0,'checks':C},sort_keys=True))
