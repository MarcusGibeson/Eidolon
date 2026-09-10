import tempfile
from conscious_agent.conversation_health_v2694 import build_conversation_health
from conscious_agent.conversation_policy_review_v2695 import build_conversation_policy_review_packet
checks=[]
def ck(x):checks.append(bool(x))
with tempfile.TemporaryDirectory() as td:
 h=build_conversation_health(td);ck(h['state']=='nominal');ck(not h['automatic_policy_change']);ck(not h['authority_granted']);r=build_conversation_policy_review_packet(h);ck(not r['review_required']);ck(not r['automatic_prompt_change'])
synthetic={'state':'degraded','concern_count':3,'concerns':['response_grounding_review_due','repeated_output_grounding_concerns','conversation_target_coherence_review_due'],'health_digest':'a'*64};r=build_conversation_policy_review_packet(synthetic);ck(r['review_required']);ck(len(r['action_codes'])==3);ck(not r['automatic_policy_change']);ck(not r['automatic_response_rewrite']);ck(not r['authority_granted'])
print({'ok':all(checks),'passed':sum(checks),'total':len(checks)});raise SystemExit(0 if all(checks) else 1)
