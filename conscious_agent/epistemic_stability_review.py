from __future__ import annotations
"""v1118.7 deterministic revision reliability and epistemic stability review."""
from copy import deepcopy
from belief_revision_lineage import BeliefRevisionLineageStore, CONTRACT_VERSION as LINEAGE_VERSION
CONTRACT_VERSION='v1118.7'
class EpistemicStabilityReviewer:
 def __init__(self,runtime_root=None): self.lineage=BeliefRevisionLineageStore(runtime_root)
 def review(self,*,belief_id:str,minimum_evidence:int=3,operator_review_required:bool=False):
  rows=[x for x in self.lineage.snapshot().get('revisions',[]) if x.get('belief_id')==belief_id]
  outcomes=[x.get('outcome') for x in rows]; directional=[x for x in outcomes if x in {'weaken','strengthen','suspend','replace','retain'}]
  reversals=sum(1 for a,b in zip(directional,directional[1:]) if (a,b) in {('weaken','strengthen'),('strengthen','weaken'),('retain','replace'),('replace','retain'),('suspend','strengthen'),('strengthen','suspend')})
  if len(rows)<minimum_evidence: status='insufficient_evidence'; unstable=False; recurring=False; suppressed=True
  else: recurring=max((outcomes.count(x) for x in set(outcomes)),default=0)>=3; unstable=reversals>=2; status='oscillation_detected' if unstable else ('recurrence_detected' if recurring else 'stable_or_indeterminate'); suppressed=False
  proposal=None
  if (unstable or recurring) and operator_review_required:
   proposal={'proposal_id':f'epistemic-policy-{belief_id[:24]}-{len(rows)}','proposal_type':'operator_reviewed_epistemic_policy','state':'proposed','approved':False,'authorized':False,'applied':False,'can_mutate_belief':False,'can_change_policy':False}
  return {'ok':True,'contract_version':CONTRACT_VERSION,'lineage_contract_version':LINEAGE_VERSION,'belief_id':belief_id,'sample_size':len(rows),'outcomes':outcomes,'reversal_count':reversals,'recurrence_detected':recurring,'oscillation_detected':unstable,'false_instability_suppressed':suppressed,'status':status,'revision_reliability':0.0 if not rows else round(max(0.0,1.0-(reversals/max(1,len(rows)-1))),4),'operator_review_proposal':proposal,'belief_mutated':False,'proposal_applied':False,'approval_granted':False,'authorization_granted':False,'external_action_executed':False,'hidden_reasoning_exposed':False,'runtime_mutated':False}
 def inspection_summary(self):
  base=self.lineage.inspection_summary(); ids=sorted({x.get('belief_id') for x in base.get('recent_revisions',[]) if x.get('belief_id')}); reviews=[self.review(belief_id=x) for x in ids[-24:]]
  return {'ok':True,'contract_version':CONTRACT_VERSION,'lineage_contract_version':LINEAGE_VERSION,'belief_count':len(ids),'reviews':reviews,'authority_boundary':deepcopy(base.get('authority_boundary',{})),'belief_mutated':False,'proposal_applied':False,'approval_granted':False,'authorization_granted':False,'external_action_executed':False,'hidden_reasoning_exposed':False,'runtime_mutated':False}
def build_epistemic_stability_review(runtime_root=None): return EpistemicStabilityReviewer(runtime_root).inspection_summary()
