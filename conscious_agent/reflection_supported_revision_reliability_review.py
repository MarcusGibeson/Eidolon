from __future__ import annotations
"""v1128.7 correction-history and revision integration reliability review."""
from copy import deepcopy
from reflection_supported_revision_outcome_lineage import ReflectionSupportedRevisionOutcomeLineageStore, CONTRACT_VERSION as LINEAGE_VERSION
CONTRACT_VERSION='v1128.7'
class ReflectionSupportedRevisionReliabilityReviewer:
 def __init__(self,runtime_root=None): self.lineage=ReflectionSupportedRevisionOutcomeLineageStore(runtime_root)
 def review(self,*,target_type:str,target_id:str,minimum_evidence:int=3,operator_review_required:bool=False):
  rows=[x for x in self.lineage.snapshot().get('outcomes',[]) if x.get('target_type')==target_type and x.get('target_id')==target_id]; outcomes=[x.get('outcome') for x in rows]
  recommendations=sum(1 for x in outcomes if str(x).startswith('recommend_')); nonapply=outcomes.count('deliberate_non_application'); unresolved=outcomes.count('unresolved'); recovery=outcomes.count('defer_for_recovery'); operator=outcomes.count('defer_for_operator_review'); corrections=sum(1 for x in rows if x.get('correction_of_revision_outcome_id')); reversals=sum(1 for a,b in zip(outcomes,outcomes[1:]) if a!=b)
  suppressed=len(rows)<minimum_evidence
  if suppressed: status='insufficient_evidence'
  elif corrections>=2: status='repeated_correction_pattern'
  elif unresolved+recovery>=2: status='persistent_revision_uncertainty'
  elif reversals>=3: status='revision_recommendation_instability'
  elif recommendations>=3 and nonapply==0: status='possible_revision_pressure'
  else: status='stable_or_indeterminate'
  proposal=None
  if operator_review_required and status not in {'insufficient_evidence','stable_or_indeterminate'}: proposal={'proposal_id':f'revision-policy-{target_type}-{target_id[:16]}-{len(rows)}','proposal_type':'operator_reviewed_revision_policy','state':'proposed','approved':False,'authorized':False,'applied':False}
  reliability=0.0 if not rows else round(max(0.0,1.0-((unresolved+recovery+corrections*.5+reversals*.15)/max(1,len(rows)))),4)
  return {'ok':True,'contract_version':CONTRACT_VERSION,'lineage_contract_version':LINEAGE_VERSION,'target_type':target_type,'target_id':target_id,'sample_size':len(rows),'outcomes':outcomes,'recommendation_count':recommendations,'non_application_count':nonapply,'unresolved_count':unresolved,'recovery_deferral_count':recovery,'operator_deferral_count':operator,'correction_count':corrections,'reversal_count':reversals,'false_pattern_suppressed':suppressed,'status':status,'revision_reliability':reliability,'operator_review_proposal':proposal,'raw_content_exposed':False,'hidden_reasoning_exposed':False,'revision_applied':False,'target_revised':False,'provider_contacted':False,'message_sent':False,'external_action_executed':False}
 def inspection_summary(self):
  base=self.lineage.inspection_summary(); keys=sorted({(x.get('target_type'),x.get('target_id')) for x in base.get('recent_outcomes',[]) if x.get('target_type') and x.get('target_id')}); reviews=[self.review(target_type=a,target_id=b) for a,b in keys[-24:]]
  return {'ok':True,'contract_version':CONTRACT_VERSION,'lineage_contract_version':LINEAGE_VERSION,'review_count':len(reviews),'reviews':reviews,'visible_status':{'active_reviews':len(reviews),'raw_content_exposed':False,'hidden_reasoning_exposed':False},'raw_content_exposed':False,'hidden_reasoning_exposed':False,'authority_boundary':deepcopy(base.get('authority_boundary',{})),'revision_applied':False,'target_revised':False,'provider_contacted':False,'message_sent':False,'external_action_executed':False}
def build_reflection_supported_revision_reliability_review_inspection(runtime_root=None): return ReflectionSupportedRevisionReliabilityReviewer(runtime_root).inspection_summary()
