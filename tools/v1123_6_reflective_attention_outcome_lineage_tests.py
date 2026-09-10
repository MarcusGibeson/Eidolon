from pathlib import Path
import tempfile
from conscious_agent.reflective_attention_outcome_lineage import ReflectiveAttentionOutcomeLineageStore
passed=0
def req(x):
 global passed; assert x; passed+=1
with tempfile.TemporaryDirectory() as td:
 s=ReflectiveAttentionOutcomeLineageStore(Path(td)); a=s.record('e1',candidate_id='c1',session_id='s1',outcome='retain_for_review'); req(a['ok']); req(s.record('e1',candidate_id='c1',session_id='s1',outcome='retain_for_review')['idempotent']); b=s.record('e2',candidate_id='c1',session_id='s2',outcome='defer_for_recovery',predecessor_outcome_id=a['result']['outcome_id'],interruption_state='interrupted'); req(b['ok']); req(s.supersede('e3',outcome_id=a['result']['outcome_id'],successor_outcome_id=b['result']['outcome_id'])['result']['history_preserved']); x=s.inspection_summary(); req(x['contract_version']=='v1123.6' and x['outcome_count']==2); req(x['history_preserved']); req(not any(x[k] for k in ('attention_selected','reflection_created','intention_created','initiative_created','message_sent','notification_created','provider_contacted','browsing_performed','policy_applied','approval_granted','authorization_granted','external_action_executed','release_promoted','release_certified'))); req(not x['hidden_reasoning_exposed'])
print(f'v1123.6 reflective attention outcome lineage: {passed}/8 passed')
