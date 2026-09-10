from __future__ import annotations
"""v1132.7 world-model continuity, reliability, correction stability, and false-pattern review."""
from copy import deepcopy
from revisable_world_model_outcome_lineage import RevisableWorldModelOutcomeLineageStore, CONTRACT_VERSION as LINEAGE_VERSION
CONTRACT_VERSION='v1132.7'
class RevisableWorldModelReliabilityReviewer:
 def __init__(self,runtime_root=None): self.lineage=RevisableWorldModelOutcomeLineageStore(runtime_root)
 def review(self,*,relation_category:str,minimum_evidence:int=3,operator_review_required:bool=False):
  rows=[x for x in self.lineage.snapshot().get('outcomes',[]) if relation_category in x.get('relation_categories',[])]; outs=[x.get('outcome') for x in rows]; accepted=sum(x in {'relationship_acceptance_recommended','causal_relationship_review_recommended','contradiction_reconciliation_recommended','correction_acceptance_recommended','temporal_relationship_review_recommended'} for x in outs); rejected=outs.count('deliberate_non_acceptance'); deferred=sum(str(x).startswith('defer_') or str(x).startswith('await_') for x in outs); continuity_failures=sum(1 for x in rows if x.get('continuity_state') in {'broken','lost','stale'}); corrections=sum(1 for x in rows if x.get('correction_state') not in {'','none'}); reversals=sum(1 for a,b in zip(outs,outs[1:]) if a!=b); suppressed=len(rows)<minimum_evidence
  if suppressed: status='insufficient_evidence'
  elif continuity_failures>=2: status='world_model_continuity_failure'
  elif corrections>=3 and reversals>=2: status='correction_instability'
  elif accepted>=4 and rejected==0 and relation_category=='may_cause': status='possible_causal_overreach'
  elif rejected>=4 and accepted==0: status='possible_under_acceptance'
  elif reversals>=4: status='world_model_recommendation_instability'
  else: status='stable_or_indeterminate'
  proposal=None
  if operator_review_required and status not in {'insufficient_evidence','stable_or_indeterminate'}: proposal={'proposal_id':f'world-model-policy-{relation_category}-{len(rows)}','proposal_type':'operator_reviewed_world_model_policy','state':'proposed','approved':False,'authorized':False,'applied':False}
  return {'ok':True,'contract_version':CONTRACT_VERSION,'lineage_contract_version':LINEAGE_VERSION,'relation_category':relation_category,'sample_size':len(rows),'accepted_count':accepted,'non_acceptance_count':rejected,'deferred_count':deferred,'continuity_failure_count':continuity_failures,'correction_count':corrections,'reversal_count':reversals,'false_pattern_suppressed':suppressed,'status':status,'operator_review_proposal':proposal,'raw_content_exposed':False,'hidden_reasoning_exposed':False,'external_action_executed':False}
 def inspection_summary(self):
  base=self.lineage.inspection_summary(); relations=sorted({p for x in base.get('recent_outcomes',[]) for p in x.get('relation_categories',[])}); reviews=[self.review(relation_category=p) for p in relations[-24:]]
  return {'ok':True,'contract_version':CONTRACT_VERSION,'lineage_contract_version':LINEAGE_VERSION,'review_count':len(reviews),'reviews':reviews,'visible_status':{'recorded_outcomes':base.get('outcome_count',0),'active_reviews':len(reviews),'accepted_count':sum(base.get('outcome_counts',{}).get(k,0) for k in ('relationship_acceptance_recommended','causal_relationship_review_recommended','contradiction_reconciliation_recommended','correction_acceptance_recommended','temporal_relationship_review_recommended')),'deliberate_non_acceptance_count':base.get('outcome_counts',{}).get('deliberate_non_acceptance',0),'raw_content_exposed':False,'hidden_reasoning_exposed':False},'authority_boundary':deepcopy(base.get('authority_boundary',{})),'raw_content_exposed':False,'hidden_reasoning_exposed':False,'provider_contacted':False,'external_action_executed':False}
def build_revisable_world_model_reliability_review_inspection(runtime_root=None): return RevisableWorldModelReliabilityReviewer(runtime_root).inspection_summary()
