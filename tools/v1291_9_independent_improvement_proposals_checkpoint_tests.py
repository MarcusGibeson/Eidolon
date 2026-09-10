from __future__ import annotations
import json,os,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.dont_write_bytecode=True;os.environ['PYTHONDONTWRITEBYTECODE']='1';sys.path.insert(0,str(ROOT/'conscious_agent'))
from independent_improvement_proposals_checkpoint import independent_improvement_proposals_checkpoint
C=[]
def req(v,l):
 if not v:raise AssertionError(l)
 C.append(l)
r=independent_improvement_proposals_checkpoint(ROOT);req(r['ok'],'checkpoint');req(r['contract_version']=='v1291.9','version');req(all(r['checks'].values()),'checks');req(r['checks']['evidence_backed_only'],'evidence');req(r['checks']['todo_not_automatically_work'] and r['checks']['uncertainty_not_automatically_work'] and r['checks']['aesthetic_preference_not_automatically_work'],'noise_suppressed');req(r['checks']['stale_duplicate_private_low_value_suppressed'],'weak_suppressed');req(r['checks']['operator_selection_required'],'operator');req(r['checks']['native_operator_proposal_review_pending'],'native_pending');req(r['next']=='v1292 Value and Risk Deliberation' and r['v1292_started'] and r['checks']['v1292_transition_coherent'],'next_transition');req(r['read_only'] and not r['project_mutation_authorized'] and not r['release_authorized'],'readonly')
print(json.dumps({'ok':True,'suite':'v1291.9-independent-improvement-proposals-checkpoint','passed':len(C),'failed':0,'checks':C},sort_keys=True))
