from pathlib import Path
import tempfile
from conscious_agent.reflective_focus_outcome_lineage import ReflectiveFocusOutcomeLineageStore
passed=0
def req(x):
 global passed; assert x; passed+=1
with tempfile.TemporaryDirectory() as td:
 s=ReflectiveFocusOutcomeLineageStore(Path(td)); a=s.record('e1',attention_id='a1',session_id='s1',outcome='continue_bounded_focus'); req(a['ok']); req(s.record('e1',attention_id='a1',session_id='s1',outcome='continue_bounded_focus')['idempotent']); b=s.record('e2',attention_id='a1',session_id='s2',outcome='suspend_for_recovery',predecessor_outcome_id=a['result']['outcome_id'],continuity_state='interrupted'); req(b['ok']); req(s.supersede('e3',outcome_id=a['result']['outcome_id'],successor_outcome_id=b['result']['outcome_id'])['result']['history_preserved']); x=s.inspection_summary(); req(x['contract_version']=='v1124.6' and x['outcome_count']==2); req(x['history_preserved']); req(not any(x[k] for k in ('reflection_created','intention_created','initiative_created','message_sent','notification_created','provider_contacted','browsing_performed','policy_applied','approval_granted','authorization_granted','external_action_executed','release_promoted','release_certified'))); req(not x['hidden_reasoning_exposed'])
print(f'v1124.6 reflective focus outcome lineage: {passed}/8 passed')
