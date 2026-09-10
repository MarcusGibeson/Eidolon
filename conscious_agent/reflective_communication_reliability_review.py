from __future__ import annotations
"""v1129.7 communication continuity, reliability, pattern review, and false-pattern suppression."""
from copy import deepcopy
from reflective_communication_outcome_lineage import ReflectiveCommunicationOutcomeLineageStore, CONTRACT_VERSION as LINEAGE_VERSION
CONTRACT_VERSION='v1129.7'
class ReflectiveCommunicationReliabilityReviewer:
 def __init__(self,runtime_root=None): self.lineage=ReflectiveCommunicationOutcomeLineageStore(runtime_root)
 def review(self,*,purpose_category:str,minimum_evidence:int=3,operator_review_required:bool=False):
  rows=[x for x in self.lineage.snapshot().get('outcomes',[]) if purpose_category in x.get('purpose_categories',[])];outs=[x.get('outcome') for x in rows];communicate=sum(x in {'communicate_when_eligible','clarification_eligible','curiosity_question_eligible'} for x in outs);silence=outs.count('deliberate_silence');delay=outs.count('delayed_follow_up')+outs.count('defer_for_timing');interruptions=sum(1 for x in rows if not x.get('interruption_respected',True));curiosity=sum(x=='curiosity_question_eligible' for x in outs);reversals=sum(1 for a,b in zip(outs,outs[1:]) if a!=b);suppressed=len(rows)<minimum_evidence
  if suppressed:status='insufficient_evidence'
  elif interruptions>=2:status='considerate_interruption_failure'
  elif communicate>=4 and silence==0:status='possible_over_communication'
  elif silence>=4 and communicate==0:status='possible_under_communication'
  elif purpose_category=='curiosity_question' and curiosity==0 and len(rows)>=3:status='curiosity_usefulness_unproven'
  elif reversals>=4:status='communication_recommendation_instability'
  else:status='stable_or_indeterminate'
  proposal=None
  if operator_review_required and status not in {'insufficient_evidence','stable_or_indeterminate'}:proposal={'proposal_id':f'communication-policy-{purpose_category}-{len(rows)}','proposal_type':'operator_reviewed_communication_policy','state':'proposed','approved':False,'authorized':False,'applied':False}
  return {'ok':True,'contract_version':CONTRACT_VERSION,'lineage_contract_version':LINEAGE_VERSION,'purpose_category':purpose_category,'sample_size':len(rows),'communicate_count':communicate,'silence_count':silence,'delay_count':delay,'interruption_failure_count':interruptions,'curiosity_useful_count':curiosity,'reversal_count':reversals,'false_pattern_suppressed':suppressed,'status':status,'operator_review_proposal':proposal,'raw_content_exposed':False,'message_text_exposed':False,'hidden_reasoning_exposed':False,'message_sent':False,'notification_created':False,'initiative_created':False,'external_action_executed':False}
 def inspection_summary(self):
  base=self.lineage.inspection_summary();purposes=sorted({p for x in base.get('recent_outcomes',[]) for p in x.get('purpose_categories',[])});reviews=[self.review(purpose_category=p) for p in purposes[-24:]]
  return {'ok':True,'contract_version':CONTRACT_VERSION,'lineage_contract_version':LINEAGE_VERSION,'review_count':len(reviews),'reviews':reviews,'visible_status':{'recorded_outcomes':base.get('outcome_count',0),'active_reviews':len(reviews),'delayed_follow_up_count':base.get('outcome_counts',{}).get('delayed_follow_up',0),'deliberate_silence_count':base.get('outcome_counts',{}).get('deliberate_silence',0),'raw_content_exposed':False,'hidden_reasoning_exposed':False},'authority_boundary':deepcopy(base.get('authority_boundary',{})),'raw_content_exposed':False,'message_text_exposed':False,'hidden_reasoning_exposed':False,'provider_contacted':False,'message_sent':False,'notification_created':False,'initiative_created':False,'external_action_executed':False}
def build_reflective_communication_reliability_review_inspection(runtime_root=None): return ReflectiveCommunicationReliabilityReviewer(runtime_root).inspection_summary()
