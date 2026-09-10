from __future__ import annotations
"""v1130.7 inquiry continuity, reliability, pattern review, and false-pattern suppression."""
from copy import deepcopy
from genuine_inquiry_outcome_lineage import GenuineInquiryOutcomeLineageStore, CONTRACT_VERSION as LINEAGE_VERSION
CONTRACT_VERSION='v1130.7'
class GenuineInquiryReliabilityReviewer:
 def __init__(self,runtime_root=None): self.lineage=GenuineInquiryOutcomeLineageStore(runtime_root)
 def review(self,*,purpose_category:str,minimum_evidence:int=3,operator_review_required:bool=False):
  rows=[x for x in self.lineage.snapshot().get('outcomes',[]) if purpose_category in x.get('purpose_categories',[])];outs=[x.get('outcome') for x in rows];proceed=sum(x in {'internal_review_eligible','clarification_eligible','bounded_inquiry_eligible'} for x in outs);no_inquiry=outs.count('deliberate_no_inquiry');defer=sum(str(x).startswith('defer_') or x=='await_prerequisite' for x in outs);continuity_failures=sum(1 for x in rows if x.get('continuity_state') in {'broken','lost','stale'});bounded=sum(x=='bounded_inquiry_eligible' for x in outs);reversals=sum(1 for a,b in zip(outs,outs[1:]) if a!=b);suppressed=len(rows)<minimum_evidence
  if suppressed:status='insufficient_evidence'
  elif continuity_failures>=2:status='inquiry_continuity_failure'
  elif proceed>=4 and no_inquiry==0:status='possible_over_inquiry'
  elif no_inquiry>=4 and proceed==0:status='possible_under_inquiry'
  elif purpose_category=='pursue_curiosity' and bounded==0 and len(rows)>=3:status='curiosity_usefulness_unproven'
  elif reversals>=4:status='inquiry_recommendation_instability'
  else:status='stable_or_indeterminate'
  proposal=None
  if operator_review_required and status not in {'insufficient_evidence','stable_or_indeterminate'}:proposal={'proposal_id':f'inquiry-policy-{purpose_category}-{len(rows)}','proposal_type':'operator_reviewed_inquiry_policy','state':'proposed','approved':False,'authorized':False,'applied':False}
  return {'ok':True,'contract_version':CONTRACT_VERSION,'lineage_contract_version':LINEAGE_VERSION,'purpose_category':purpose_category,'sample_size':len(rows),'proceed_count':proceed,'no_inquiry_count':no_inquiry,'defer_count':defer,'continuity_failure_count':continuity_failures,'bounded_inquiry_count':bounded,'reversal_count':reversals,'false_pattern_suppressed':suppressed,'status':status,'operator_review_proposal':proposal,'raw_content_exposed':False,'question_text_exposed':False,'hidden_reasoning_exposed':False,'message_sent':False,'notification_created':False,'initiative_created':False,'external_action_executed':False}
 def inspection_summary(self):
  base=self.lineage.inspection_summary();purposes=sorted({p for x in base.get('recent_outcomes',[]) for p in x.get('purpose_categories',[])});reviews=[self.review(purpose_category=p) for p in purposes[-24:]]
  return {'ok':True,'contract_version':CONTRACT_VERSION,'lineage_contract_version':LINEAGE_VERSION,'review_count':len(reviews),'reviews':reviews,'visible_status':{'recorded_outcomes':base.get('outcome_count',0),'active_reviews':len(reviews),'bounded_inquiry_count':base.get('outcome_counts',{}).get('bounded_inquiry_eligible',0),'deliberate_no_inquiry_count':base.get('outcome_counts',{}).get('deliberate_no_inquiry',0),'raw_content_exposed':False,'hidden_reasoning_exposed':False},'authority_boundary':deepcopy(base.get('authority_boundary',{})),'raw_content_exposed':False,'question_text_exposed':False,'hidden_reasoning_exposed':False,'browser_contacted':False,'provider_contacted':False,'message_sent':False,'notification_created':False,'initiative_created':False,'external_action_executed':False}
def build_genuine_inquiry_reliability_review_inspection(runtime_root=None): return GenuineInquiryReliabilityReviewer(runtime_root).inspection_summary()
