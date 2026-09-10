from __future__ import annotations
"""v1119.7 deterministic repeated-inconsistency and integration stability review."""
from copy import deepcopy
from epistemic_coherence_outcome_lineage import EpistemicCoherenceOutcomeLineageStore, CONTRACT_VERSION as LINEAGE_VERSION
CONTRACT_VERSION='v1119.7'
class KnowledgeBeliefIntegrationStabilityReviewer:
 def __init__(self,runtime_root=None): self.lineage=EpistemicCoherenceOutcomeLineageStore(runtime_root)
 def review(self,*,candidate_id:str,minimum_evidence:int=3,operator_review_required:bool=False):
  rows=[x for x in self.lineage.snapshot().get('outcomes',[]) if x.get('candidate_id')==candidate_id]
  outcomes=[x.get('outcome') for x in rows]; repairs=[x for x in outcomes if x in {'merge_candidate','weaken_claim','suspend_claim','replace_dependency','retain_separation'}]
  reversals=sum(1 for a,b in zip(repairs,repairs[1:]) if (a,b) in {('merge_candidate','retain_separation'),('retain_separation','merge_candidate'),('weaken_claim','retain_separation'),('suspend_claim','retain_separation'),('replace_dependency','retain_separation')})
  if len(rows)<minimum_evidence: status='insufficient_evidence'; recurring=False; unstable=False; suppressed=True
  else:
   recurring=max((outcomes.count(x) for x in set(outcomes)),default=0)>=3; unstable=reversals>=2; status='integration_instability_detected' if unstable else ('repeated_inconsistency_detected' if recurring else 'stable_or_indeterminate'); suppressed=False
  proposal=None
  if (unstable or recurring) and operator_review_required:
   proposal={'proposal_id':f'integration-policy-{candidate_id[:24]}-{len(rows)}','proposal_type':'operator_reviewed_knowledge_belief_integration_policy','state':'proposed','approved':False,'authorized':False,'applied':False,'can_repair_records':False,'can_merge_records':False,'can_change_policy':False}
  reliability=0.0 if not rows else round(max(0.0,1.0-(reversals/max(1,len(rows)-1))),4)
  return {'ok':True,'contract_version':CONTRACT_VERSION,'lineage_contract_version':LINEAGE_VERSION,'candidate_id':candidate_id,'sample_size':len(rows),'outcomes':outcomes,'reversal_count':reversals,'repeated_inconsistency_detected':recurring,'integration_instability_detected':unstable,'false_instability_suppressed':suppressed,'status':status,'integration_reliability':reliability,'operator_review_proposal':proposal,'records_repaired':False,'records_merged':False,'proposal_applied':False,'approval_granted':False,'authorization_granted':False,'external_action_executed':False,'hidden_reasoning_exposed':False,'runtime_mutated':False}
 def inspection_summary(self):
  base=self.lineage.inspection_summary(); ids=sorted({x.get('candidate_id') for x in base.get('recent_outcomes',[]) if x.get('candidate_id')}); reviews=[self.review(candidate_id=x) for x in ids[-24:]]
  return {'ok':True,'contract_version':CONTRACT_VERSION,'lineage_contract_version':LINEAGE_VERSION,'candidate_count':len(ids),'reviews':reviews,'authority_boundary':deepcopy(base.get('authority_boundary',{})),'records_repaired':False,'records_merged':False,'proposal_applied':False,'approval_granted':False,'authorization_granted':False,'external_action_executed':False,'hidden_reasoning_exposed':False,'runtime_mutated':False}
def build_knowledge_belief_integration_stability_review(runtime_root=None): return KnowledgeBeliefIntegrationStabilityReviewer(runtime_root).inspection_summary()
