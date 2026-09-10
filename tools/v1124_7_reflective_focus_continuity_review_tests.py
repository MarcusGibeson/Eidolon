from pathlib import Path
import tempfile
from conscious_agent.reflective_focus_outcome_lineage import ReflectiveFocusOutcomeLineageStore
from conscious_agent.reflective_focus_continuity_review import ReflectiveFocusContinuityReviewer
passed=0
def req(x):
 global passed; assert x; passed+=1
with tempfile.TemporaryDirectory() as td:
 root=Path(td); s=ReflectiveFocusOutcomeLineageStore(root)
 for i,o in enumerate(['continue_bounded_focus','suspend_for_recovery','continue_bounded_focus','suspend_for_recovery']): s.record(f'e{i}',attention_id='a1',session_id=f's{i}',outcome=o,continuity_state='resumed' if i==3 else 'interrupted')
 r=ReflectiveFocusContinuityReviewer(root).review(attention_id='a1',operator_review_required=True); req(r['contract_version']=='v1124.7'); req(r['focus_instability_detected']); req(r['interruption_count']==4 and r['resumption_count']==1); req(r['operator_review_proposal']['applied'] is False); req(r['focus_reliability']>=0); req(not any(r[k] for k in ('reflection_created','intention_created','initiative_created','message_sent','notification_created','provider_contacted','browsing_performed','policy_applied','approval_granted','authorization_granted','external_action_executed'))); req(ReflectiveFocusContinuityReviewer(root).review(attention_id='missing')['false_pattern_suppressed']); req(not r['hidden_reasoning_exposed'])
print(f'v1124.7 reflective focus continuity review: {passed}/8 passed')
