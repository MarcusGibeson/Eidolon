from __future__ import annotations
"""v1134.7 prospective planning continuity, risk stability, over-planning, and false-pattern review."""
from copy import deepcopy
from prospective_planning_outcome_lineage import ProspectivePlanningOutcomeLineageStore, CONTRACT_VERSION as LINEAGE_VERSION
CONTRACT_VERSION='v1134.7'
class ProspectivePlanningReliabilityReviewer:
 def __init__(self,runtime_root=None): self.lineage=ProspectivePlanningOutcomeLineageStore(runtime_root)
 def review(self,*,plan_class:str,minimum_evidence:int=3,operator_review_required:bool=False):
  rows=[x for x in self.lineage.snapshot().get('outcomes',[]) if x.get('plan_class')==plan_class]; outs=[x.get('outcome') for x in rows]; accepted=outs.count('plan_recommended'); deferred=sum(x.get('lifecycle_state')=='deferred' for x in rows); abandoned=sum(x.get('lifecycle_state') in {'abandoned','retired','obsolete'} for x in rows); completed=sum(x.get('lifecycle_state')=='completed' for x in rows); blocked=sum(x.get('lifecycle_state')=='blocked' for x in rows); continuity_failures=sum(x.get('continuity_state') in {'broken','lost','stale'} for x in rows); reversals=sum(1 for a,b in zip(outs,outs[1:]) if a!=b); suppressed=len(rows)<minimum_evidence
  if suppressed: status='insufficient_evidence'
  elif continuity_failures>=2: status='planning_continuity_failure'
  elif accepted>=5 and completed==0 and abandoned==0: status='possible_over_planning'
  elif abandoned>=3 and completed==0: status='repeated_plan_abandonment'
  elif blocked>=3: status='persistent_planning_blockage'
  elif reversals>=4: status='planning_priority_instability'
  elif deferred>=3: status='repeated_plan_deferral'
  else: status='stable_or_indeterminate'
  proposal=None
  if operator_review_required and status not in {'insufficient_evidence','stable_or_indeterminate'}: proposal={'proposal_id':f'planning-policy-{plan_class}-{len(rows)}','proposal_type':'operator_reviewed_planning_policy','state':'proposed','approved':False,'authorized':False,'applied':False}
  return {'ok':True,'contract_version':CONTRACT_VERSION,'lineage_contract_version':LINEAGE_VERSION,'plan_class':plan_class,'sample_size':len(rows),'accepted_count':accepted,'deferred_count':deferred,'abandoned_count':abandoned,'completed_count':completed,'blocked_count':blocked,'continuity_failure_count':continuity_failures,'reversal_count':reversals,'false_pattern_suppressed':suppressed,'status':status,'operator_review_proposal':proposal,'raw_content_exposed':False,'hidden_reasoning_exposed':False,'external_action_executed':False}
 def inspection_summary(self):
  base=self.lineage.inspection_summary(); classes=sorted({x.get('plan_class') for x in base.get('recent_outcomes',[]) if x.get('plan_class')}); reviews=[self.review(plan_class=x) for x in classes[-24:]]
  return {'ok':True,'contract_version':CONTRACT_VERSION,'lineage_contract_version':LINEAGE_VERSION,'review_count':len(reviews),'reviews':reviews,'visible_status':{'recorded_outcomes':base.get('outcome_count',0),'active_reviews':len(reviews),'active_count':base.get('lifecycle_counts',{}).get('active',0),'deferred_count':base.get('lifecycle_counts',{}).get('deferred',0),'blocked_count':base.get('lifecycle_counts',{}).get('blocked',0),'completed_count':base.get('lifecycle_counts',{}).get('completed',0),'retired_count':base.get('lifecycle_counts',{}).get('retired',0),'raw_content_exposed':False,'hidden_reasoning_exposed':False},'authority_boundary':deepcopy(base.get('authority_boundary',{})),'raw_content_exposed':False,'hidden_reasoning_exposed':False,'provider_contacted':False,'external_action_executed':False}
def build_prospective_planning_reliability_review_inspection(runtime_root=None): return ProspectivePlanningReliabilityReviewer(runtime_root).inspection_summary()
