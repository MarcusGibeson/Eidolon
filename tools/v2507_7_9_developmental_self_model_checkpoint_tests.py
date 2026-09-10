from __future__ import annotations
import json,sys,tempfile,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
sys.dont_write_bytecode=True
from conscious_agent.developmental_self_model_bridge_v2507 import observe_from_outcome_receipt
from conscious_agent.developmental_self_model_v2507 import DevelopmentalSelfModelStore
checks=[]
def req(v,n):checks.append(n);assert v,n
def d(s):return hashlib.sha256(s.encode()).hexdigest()
with tempfile.TemporaryDirectory(prefix='eidolon-v2507-7-9-') as td:
 root=Path(td)
 for i in range(3):
  receipt={'evidence_digest':d(f'run-{i}'),'source_kind':'development_outcome','outcome_code':'bounded_change_preferred','raw_output':'must_not_persist'}
  r=observe_from_outcome_receipt(f'obs-{i}',runtime_root=root,receipt=receipt,trait_code='reversibility_preference',domain='software_development');req(r['ok'],f'bridge_{i}')
 s=DevelopmentalSelfModelStore(root);e=s.evaluate_trait('reversibility_preference');req(e['eligible_for_trait_candidate'],'cross_domain_candidate_ready');c=s.stage_trait_candidate('stage',trait_code='reversibility_preference');req(c['ok'],'staged');req(c['state']=='supported','supported');req(not c['trait_applied'],'unapplied');ins=s.inspection_summary();req(ins['trait_candidate_count']==1,'one_candidate');req(not ins['provider_contacted'] and not ins['external_action_executed'],'no_external');req(not ins['identity_rewritten'],'identity_unchanged');req(not ins['authority_boundary']['can_claim_consciousness'],'no_consciousness_claim');req(all('raw_output' not in json.dumps(x) for x in ins['recent_trait_candidates']),'raw_receipt_absent')
print(json.dumps({'ok':True,'checkpoint_version':'2507.9','contract':'Developmental Evidence-Based Self-Model Foundations','passed':len(checks),'total':len(checks),'checks':checks},sort_keys=True))
