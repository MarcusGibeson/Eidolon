from __future__ import annotations
"""v1127.7 continuous-thought interruption, stall, fixation, and reliability review."""
from copy import deepcopy
from thought_thread_outcome_lineage import ThoughtThreadOutcomeLineageStore, CONTRACT_VERSION as LINEAGE_VERSION
CONTRACT_VERSION='v1127.7'
class ThoughtThreadReliabilityReviewer:
 def __init__(self,runtime_root=None): self.lineage=ThoughtThreadOutcomeLineageStore(runtime_root)
 def review(self,*,thread_id:str,minimum_evidence:int=3,operator_review_required:bool=False):
  rows=[x for x in self.lineage.snapshot().get('outcomes',[]) if x.get('thread_id')==thread_id]; outcomes=[x.get('outcome') for x in rows]
  pauses=outcomes.count('pause_thread'); resumes=outcomes.count('resume_thread'); unresolved=outcomes.count('remain_unresolved'); recovery=outcomes.count('defer_for_recovery'); continues=outcomes.count('continue_thread'); branches=outcomes.count('branch_thread'); conclusions=outcomes.count('conclude_thread'); interruptions=sum(1 for x in rows if x.get('interruption_state') not in {'','none'}); reversals=sum(1 for a,b in zip(outcomes,outcomes[1:]) if a!=b)
  suppressed=len(rows)<minimum_evidence
  if suppressed: status='insufficient_evidence'
  elif unresolved>=2 or recovery>=2: status='repeated_stall_or_recovery_deferral'
  elif continues>=3 and conclusions==0 and branches==0: status='possible_thread_fixation'
  elif interruptions>=2 and resumes==0: status='interruption_resumption_reliability_concern'
  elif reversals>=3: status='thread_continuity_instability'
  else: status='stable_or_indeterminate'
  proposal=None
  if operator_review_required and status not in {'insufficient_evidence','stable_or_indeterminate'}: proposal={'proposal_id':f'thought-thread-policy-{thread_id[:20]}-{len(rows)}','proposal_type':'operator_reviewed_thought_thread_policy','state':'proposed','approved':False,'authorized':False,'applied':False}
  reliability=0.0 if not rows else round(max(0.0,1.0-((unresolved+recovery+interruptions*.5+reversals*.15)/max(1,len(rows)))),4)
  return {'ok':True,'contract_version':CONTRACT_VERSION,'lineage_contract_version':LINEAGE_VERSION,'thread_id':thread_id,'sample_size':len(rows),'outcomes':outcomes,'pause_count':pauses,'resume_count':resumes,'unresolved_count':unresolved,'recovery_deferral_count':recovery,'continue_count':continues,'branch_count':branches,'conclusion_count':conclusions,'interruption_count':interruptions,'reversal_count':reversals,'false_pattern_suppressed':suppressed,'status':status,'thread_reliability':reliability,'operator_review_proposal':proposal,'raw_content_exposed':False,'hidden_reasoning_exposed':False,'provider_contacted':False,'reflection_created':False,'belief_updated':False,'goal_updated':False,'self_model_updated':False,'message_sent':False,'initiative_created':False,'external_action_executed':False}
 def inspection_summary(self):
  base=self.lineage.inspection_summary(); ids=sorted({x.get('thread_id') for x in base.get('recent_outcomes',[]) if x.get('thread_id')}); reviews=[self.review(thread_id=x) for x in ids[-24:]]
  return {'ok':True,'contract_version':CONTRACT_VERSION,'lineage_contract_version':LINEAGE_VERSION,'review_count':len(reviews),'reviews':reviews,'visible_status':{'active_reviews':len(reviews),'raw_content_exposed':False,'hidden_reasoning_exposed':False},'authority_boundary':deepcopy(base.get('authority_boundary',{})),'provider_contacted':False,'reflection_created':False,'belief_updated':False,'goal_updated':False,'self_model_updated':False,'message_sent':False,'initiative_created':False,'external_action_executed':False}
def build_thought_thread_reliability_review_inspection(runtime_root=None): return ThoughtThreadReliabilityReviewer(runtime_root).inspection_summary()
