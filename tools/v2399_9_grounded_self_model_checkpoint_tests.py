from __future__ import annotations
import hashlib, json, os, sys, tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/'conscious_agent')); sys.dont_write_bytecode=True
os.environ['EIDOLON_DATA_DIR']=tempfile.mkdtemp(prefix='eidolon-v2399-self-data-')
from grounded_self_model_v2300 import *
checks=[]
def req(v,n): checks.append(n); assert v,n
evidence={'evidence_owner':'capability_receipt','capability_code':'memory_recall','status':'verified'}
evidence_digest=hashlib.sha256(json.dumps(evidence,sort_keys=True,separators=(',',':')).encode()).hexdigest()
cap=[{'capability_code':'memory_recall','status':'verified','evidence_digest':evidence_digest,'evidence_payload':evidence},{'capability_code':'fake','status':'verified','evidence_digest':'bad'}]
sm=build_grounded_self_model(capability_receipts=cap,known_limitations=['native evidence pending'],runtime_configuration_digest='b'*64)
req(sm['ok'] and sm['release_identity']['working_source_version'],'release_identity_grounded')
req(len(sm['capabilities'])==1 and sm['rejected_capability_claim_count']==1,'unsupported_capability_claim_rejected')
req(sm['consciousness_claim_status']=='unknown_not_established','consciousness_not_claimed')
req(sm['capability_does_not_imply_authority'],'capability_not_authority')
req(not build_grounded_self_model(runtime_configuration_digest='bad')['ok'],'invalid_runtime_digest_rejected')
goals=[{'goal_id':'g1','objective_digest':'c'*64,'priority_code':'operator_high','required_authority_codes':['read_only'],'required_resource_codes':[]},{'goal_id':'g2','objective_digest':'d'*64,'priority_code':'low','required_authority_codes':[],'required_resource_codes':['gpu_busy']}]
ga=assess_goal_coherence(goals,operator_priority_codes=['operator_high'],resource_constraint_codes=['gpu_busy'],protected_authority_codes=['read_only'])
req(ga['ok'] and ga['goals'][0]['disposition']=='retain','operator_aligned_goal_retained')
req(ga['goals'][1]['disposition']=='defer_resource_constraint','resource_constrained_goal_deferred')
req(all(g['original_objective_preserved'] for g in ga['goals']),'original_objectives_preserved')
bad=assess_goal_coherence([{'goal_id':'g3','objective_digest':'bad'}])
req(not bad['ok'] and bad['malformed_goal_count']==1,'ungrounded_goal_rejected')
integ=integrate_self_model_and_goals(self_model=sm,goal_assessment=ga)
req(integ['ok'] and integ['self_model_is_evidence_projection_not_persona_fiction'],'self_model_goal_integration_grounded')
req(integ['operator_priority_preserved'] and integ['known_limitations_preserved'],'priority_and_limits_preserved')
req(all(not integ[k] for k in ('self_claim_committed','goal_mutated','source_modified','authority_expanded')),'self_model_authority_inert')
print(json.dumps({'suite':'v2399.9-grounded-self-model','ok':True,'passed':len(checks),'failed':0,'checks':checks},sort_keys=True))
