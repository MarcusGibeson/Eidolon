import tempfile
from conscious_agent.conversation_target_outcome_learning_v2690 import build_conversation_target_outcome
from conscious_agent.conversation_target_outcome_history_v2691 import append_conversation_target_outcome,build_conversation_target_learning_profile
checks=[]
def ck(x):checks.append(bool(x))
a=build_conversation_target_outcome({'applied':True,'grounded_repair_applied':True,'duplicate_sentences_removed':2});ck(a['severity']=='high');ck(a['repair_signal_count']==2);ck(not a['conversation_policy_mutated'])
with tempfile.TemporaryDirectory() as td:
 for i in range(5):append_conversation_target_outcome(a,operation_id=f'op{i}',runtime_root=td)
 p=build_conversation_target_learning_profile(td);ck(p['state']=='conversation_coherence_review_due');ck(p['repair_event_count']==5);ck(not p['automatic_policy_change']);ck(not p['raw_response_stored']);ck(not p['authority_granted'])
print({'ok':all(checks),'passed':sum(checks),'total':len(checks)});raise SystemExit(0 if all(checks) else 1)
