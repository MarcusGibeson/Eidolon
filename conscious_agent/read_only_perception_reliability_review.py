from __future__ import annotations
"""v1131.7 perception continuity, reliability, pattern review, and false-pattern suppression."""
from copy import deepcopy
from read_only_perception_outcome_lineage import ReadOnlyPerceptionOutcomeLineageStore, CONTRACT_VERSION as LINEAGE_VERSION
CONTRACT_VERSION='v1131.7'
class ReadOnlyPerceptionReliabilityReviewer:
 def __init__(self,runtime_root=None): self.lineage=ReadOnlyPerceptionOutcomeLineageStore(runtime_root)
 def review(self,*,category:str,minimum_evidence:int=3,operator_review_required:bool=False):
  rows=[x for x in self.lineage.snapshot().get('outcomes',[]) if category in x.get('categories',[])]; outs=[x.get('outcome') for x in rows]; selected=sum(x in {'structural_review_eligible','failure_review_prioritized','changed_file_review_prioritized','completed_work_review_eligible','project_state_review_eligible','system_event_review_eligible'} for x in outs); declined=outs.count('deliberate_no_perception'); deferred=sum(str(x).startswith('defer_') or x=='await_prerequisite' for x in outs); continuity_failures=sum(1 for x in rows if x.get('continuity_state') in {'broken','lost','stale'}); stale_observations=sum(1 for x in rows if x.get('observation_freshness') in {'stale','expired','unknown'}); reversals=sum(1 for a,b in zip(outs,outs[1:]) if a!=b); suppressed=len(rows)<minimum_evidence
  if suppressed:status='insufficient_evidence'
  elif continuity_failures>=2:status='perception_continuity_failure'
  elif stale_observations>=2:status='stale_perception_pressure'
  elif selected>=4 and declined==0:status='possible_over_perception'
  elif declined>=4 and selected==0:status='possible_under_perception'
  elif category in {'failure','changed_file'} and selected==0 and len(rows)>=3:status='important_perception_missed'
  elif reversals>=4:status='perception_recommendation_instability'
  else:status='stable_or_indeterminate'
  proposal=None
  if operator_review_required and status not in {'insufficient_evidence','stable_or_indeterminate'}:proposal={'proposal_id':f'perception-policy-{category}-{len(rows)}','proposal_type':'operator_reviewed_perception_policy','state':'proposed','approved':False,'authorized':False,'applied':False}
  return {'ok':True,'contract_version':CONTRACT_VERSION,'lineage_contract_version':LINEAGE_VERSION,'category':category,'sample_size':len(rows),'selected_count':selected,'deliberate_no_perception_count':declined,'defer_count':deferred,'continuity_failure_count':continuity_failures,'stale_observation_count':stale_observations,'reversal_count':reversals,'false_pattern_suppressed':suppressed,'status':status,'operator_review_proposal':proposal,'raw_file_content_exposed':False,'raw_event_payload_exposed':False,'hidden_reasoning_exposed':False,'filesystem_modified':False,'message_sent':False,'notification_created':False,'external_action_executed':False}
 def inspection_summary(self):
  base=self.lineage.inspection_summary(); categories=sorted({p for x in base.get('recent_outcomes',[]) for p in x.get('categories',[])}); reviews=[self.review(category=p) for p in categories[-24:]]
  return {'ok':True,'contract_version':CONTRACT_VERSION,'lineage_contract_version':LINEAGE_VERSION,'review_count':len(reviews),'reviews':reviews,'visible_status':{'recorded_outcomes':base.get('outcome_count',0),'active_reviews':len(reviews),'prioritized_failure_count':base.get('outcome_counts',{}).get('failure_review_prioritized',0),'prioritized_change_count':base.get('outcome_counts',{}).get('changed_file_review_prioritized',0),'deliberate_no_perception_count':base.get('outcome_counts',{}).get('deliberate_no_perception',0),'raw_content_exposed':False,'hidden_reasoning_exposed':False},'authority_boundary':deepcopy(base.get('authority_boundary',{})),'raw_file_content_exposed':False,'raw_event_payload_exposed':False,'hidden_reasoning_exposed':False,'filesystem_modified':False,'browser_contacted':False,'provider_contacted':False,'message_sent':False,'notification_created':False,'external_action_executed':False}
def build_read_only_perception_reliability_review_inspection(runtime_root=None): return ReadOnlyPerceptionReliabilityReviewer(runtime_root).inspection_summary()
