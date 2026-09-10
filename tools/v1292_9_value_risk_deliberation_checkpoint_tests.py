from __future__ import annotations
import json,os,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.dont_write_bytecode=True;os.environ['PYTHONDONTWRITEBYTECODE']='1';sys.path.insert(0,str(ROOT/'conscious_agent'))
from value_risk_deliberation_checkpoint import value_risk_deliberation_checkpoint
C=[]
def req(v,l):
 if not v:raise AssertionError(l)
 C.append(l)
r=value_risk_deliberation_checkpoint(ROOT);req(r['ok'],'checkpoint');req(r['contract_version']=='v1292.9','version');req(all(r['checks'].values()),'checks');req(r['checks']['evidence_value_risk_reversibility_cost_dependencies_uncertainty_compared'],'factors');req(r['checks']['critical_and_irreversible_risk_can_block'],'risk');req(r['checks']['ambiguous_tradeoffs_can_defer'],'defer');req(r['checks']['recommendation_explainable'],'explainable');req(r['checks']['recommendation_not_priority_mutation'] and r['checks']['recommendation_not_authority'],'boundaries');req(r['checks']['native_operator_deliberation_review_pending'],'native');req(r['next']=='v1293 Bounded Development Campaigns' and r['v1293_started'] and r['checks']['v1293_transition_coherent'],'next_transition');req(r['read_only'] and not r['priority_change_authorized'] and not r['release_authorized'],'readonly')
print(json.dumps({'ok':True,'suite':'v1292.9-value-risk-deliberation-checkpoint','passed':len(C),'failed':0,'checks':C},sort_keys=True))
