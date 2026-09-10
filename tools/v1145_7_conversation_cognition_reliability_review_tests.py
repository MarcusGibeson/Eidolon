from pathlib import Path
import tempfile
from conscious_agent.conversation_cognition_cross_cycle_continuity import ConversationCognitionCrossCycleContinuityStore
from conscious_agent.conversation_cognition_reliability_review import ConversationCognitionReliabilityReviewStore,build_conversation_cognition_reliability_review_inspection

def main():
 p=[]
 def req(v,n):
  if not v: raise AssertionError(n)
  p.append(n)
 with tempfile.TemporaryDirectory() as d:
  root=Path(d); c=ConversationCognitionCrossCycleContinuityStore(root); row=c.record('ce1',session_id='s',conversation_id='c',prior_generation_receipt_id='g1',current_generation_receipt_id='g2',source_revisions={'x':1},current_categories=['thought'],historical_categories=['memory'])
  s=ConversationCognitionReliabilityReviewStore(root); a=s.review('re1',continuity_record_ids=[row['record_id']],visible_behavior_class='grounded_reply',correction_success_count=1,coherence_score=.9,uncertainty=.1)
  req(a['state']=='reliable','reliable'); req(a['content_free'],'content_free'); req(not a['raw_output_stored'],'no_output'); req(a['correction_success_count']==1,'correction'); req(a['visible_behavior_class']=='grounded_reply','behavior'); req(not any(a['authority_boundary'].values()),'authority'); req(not a['message_sent'],'no_send')
  req(s.review('re1',continuity_record_ids=[row['record_id']],visible_behavior_class='grounded_reply')['review_id']==a['review_id'],'dedupe')
  b=s.review('re2',continuity_record_ids=[row['record_id']],visible_behavior_class='stale_reply_suppressed',stale_count=1,coherence_score=.8,uncertainty=.2); req(b['state']=='review_required','review')
  q=build_conversation_cognition_reliability_review_inspection(root); req(q['contract_version']=='v1145.7','contract'); req(q['review_count']==2,'count'); req(q['correction_effectiveness_visible'],'effectiveness'); req(q['visible_behavior_structural_only'],'privacy'); req(not q['message_sent'],'inspection_send'); req(not any(q['authority_boundary'].values()),'inspection_authority')
 print(f'v1145.7 checks: {len(p)}/{len(p)}')
if __name__=='__main__': main()
