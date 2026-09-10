from __future__ import annotations
import json,sys
from hashlib import sha256
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'conscious_agent'))
from competing_candidate_evaluation_foundations import *
C=[]
def req(v,l):
 if not v:raise AssertionError(l)
 C.append(l)
def d(s):return sha256(s.encode()).hexdigest()
a=comparison_trigger(uncertainty=70,viable_approach_count=2);req(a['comparison_required'],'uncertainty_trigger');req(not a['build_every_possible_candidate'],'bounded_not_everything');req(all(a[k] is False for k in DENIED_AUTHORITY),'trigger_no_authority')
b=comparison_trigger(uncertainty=20,viable_approach_count=2);req(not b['comparison_required'],'low_uncertainty_no_compare')
c=comparison_trigger(uncertainty=30,viable_approach_count=2,competing_hypothesis_count=2);req(c['comparison_required'],'hypothesis_trigger')
i=seal_candidate_identity(campaign_id='campaign-x',baseline_digest=d('base'),approach_digest=d('approach'),workspace_digest=d('workspace'),changed_path_digests=[d('p1'),d('p2')]);req(i['candidate_id'].startswith('candidate-'),'candidate_id');req(valid_digest(i['candidate_identity_digest']),'identity_digest');req(i['changed_path_count']==2,'changed_paths')
r=normalize_candidate_evidence(i|{'verification_run_digest':d('run'),'focused_verification_passed':True,'regression_verification_passed':True,'scope_conforming':True,'quality_disposition':'operator_ready_candidate','quality_score':90,'risk':20,'cost':30,'reversibility':90,'residual_uncertainty':10});req(r['quality_score']==90 and r['content_free'],'normalize');req(r['workspace_digest']==d('workspace'),'workspace')
try:seal_candidate_identity(campaign_id='x',baseline_digest='bad',approach_digest=d('a'),workspace_digest=d('w'),changed_path_digests=[d('p')]);bad=False
except ValueError:bad=True
req(bad,'bad_digest');req(ARCHITECTURE_LINEAGE['isolated_coding']=='v1254' and ARCHITECTURE_LINEAGE['calibrated_uncertainty']=='v1282','lineage');req(MAX_CANDIDATES==6,'candidate_bound')
print(json.dumps({'ok':True,'suite':'v1294.0-v1294.2-competing-candidate-evaluation-foundations','passed':len(C),'failed':0,'checks':C},sort_keys=True))
