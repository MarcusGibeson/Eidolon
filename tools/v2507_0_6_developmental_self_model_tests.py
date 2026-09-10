from __future__ import annotations
import json,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
sys.dont_write_bytecode=True
from conscious_agent.developmental_self_model_v2507 import DevelopmentalSelfModelStore
checks=[]
def req(v,n):checks.append(n);assert v,n
with tempfile.TemporaryDirectory(prefix='eidolon-v2507-0-6-') as td:
 s=DevelopmentalSelfModelStore(Path(td))
 evs=['a'*64,'b'*64,'c'*64]
 for i,d in enumerate(evs):s.observe(f's{i}',trait_code='verification_scope_bias',domain='software_development',polarity='support',evidence_digest=d,source_kind='development_outcome',observation_code='broad_verifier_selected')
 e=s.evaluate_trait('verification_scope_bias',domain='software_development');req(e['state']=='supported','supported');req(e['support_count']==3,'three_support');req(e['independent_support_count']==3,'independent');req(e['eligible_for_trait_candidate'],'eligible');req(e['confidence']>0.5,'confidence')
 c=s.stage_trait_candidate('candidate-1',trait_code='verification_scope_bias',domain='software_development');req(c['ok'],'candidate_staged');req(not c['trait_applied'] and not c['identity_rewritten'],'candidate_only')
 s.observe('counter',trait_code='verification_scope_bias',domain='software_development',polarity='counterexample',evidence_digest='d'*64,source_kind='benchmark_receipt',observation_code='targeted_verifier_selected')
 e2=s.evaluate_trait('verification_scope_bias',domain='software_development');req(e2['counterexample_count']==1,'counterexample');req(e2['state']=='supported_with_counterexamples','counterexample_preserved');req(e2['confidence']<e['confidence'],'confidence_revised')
 c2=s.stage_trait_candidate('candidate-2',trait_code='verification_scope_bias',domain='software_development');req(c2['revision']==2,'revision_lineage')
 dup=s.observe('counter',trait_code='verification_scope_bias',domain='software_development',polarity='counterexample',evidence_digest='d'*64,source_kind='benchmark_receipt');req(dup['idempotent'],'observation_idempotent')
 ins=s.inspection_summary();req(ins['observation_count']==4,'observations_preserved');req(ins['trait_candidate_count']==2,'trait_history_preserved');req(not ins['authority_boundary']['can_rewrite_identity'],'no_identity_write');req(not ins['hidden_reasoning_exposed'],'no_hidden_reasoning')
print(json.dumps({'ok':True,'contract':'v2507.0-v2507.6','passed':len(checks),'checks':checks},sort_keys=True))
