from pathlib import Path
import tempfile
from conscious_agent.reflective_attention_outcome_lineage import ReflectiveAttentionOutcomeLineageStore
from conscious_agent.reflective_attention_continuity_review import ReflectiveAttentionContinuityReviewer
passed=0
def req(x):
 global passed; assert x; passed+=1
with tempfile.TemporaryDirectory() as td:
 root=Path(td); s=ReflectiveAttentionOutcomeLineageStore(root)
 for i,o in enumerate(['retain_for_review','defer_for_recovery','retain_for_review','defer_for_recovery']): s.record(f'e{i}',candidate_id='c1',session_id=f's{i}',outcome=o,interruption_state='resumed' if i==3 else 'interrupted')
 r=ReflectiveAttentionContinuityReviewer(root).review(candidate_id='c1',operator_review_required=True); req(r['contract_version']=='v1123.7'); req(r['repeated_distraction_detected']); req(r['interruption_count']==4 and r['resumption_count']==1); req(r['operator_review_proposal']['applied'] is False); req(r['attention_reliability']>=0); req(not any(r[k] for k in ('attention_selected','reflection_created','intention_created','initiative_created','message_sent','notification_created','provider_contacted','browsing_performed','policy_applied','approval_granted','authorization_granted','external_action_executed'))); req(ReflectiveAttentionContinuityReviewer(root).review(candidate_id='missing')['false_pattern_suppressed']); req(not r['hidden_reasoning_exposed'])
print(f'v1123.7 reflective attention continuity review: {passed}/8 passed')
