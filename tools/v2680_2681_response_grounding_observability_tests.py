import tempfile
from conscious_agent.response_grounding_learning_profile_v2678 import append_response_grounding_feedback
from conscious_agent.response_grounding_learning_observability_v2680 import build_response_grounding_learning_observability
from conscious_agent.cognitive_observability_v2533 import build_cognitive_observability_snapshot
checks=[]
def ck(x): checks.append(bool(x))
feedback={'evidence_recorded':True,'prior_assertiveness':'grounded','prior_memory_state':'grounded_relevant_memory','disposition':'grounded_claim_corrected','adverse_calibration_evidence':True,'explicit_correction':True,'explicit_retraction':False,'feedback_digest':'a'*64}
with tempfile.TemporaryDirectory() as td:
 for _ in range(3): append_response_grounding_feedback(feedback,runtime_root=td)
 # duplicate digest intentionally dedupes to one, so add variants
 for i in range(2):
  f=dict(feedback);f['feedback_digest']=str(i+1)*64;append_response_grounding_feedback(f,runtime_root=td)
 o=build_response_grounding_learning_observability(td);ck(o['state']=='overassertion_review_due');ck(o['review_due']);ck(not o['automatic_policy_change_permitted']);ck(not o['authority_granted'])
 snap=build_cognitive_observability_snapshot(td);ck('response_grounding_learning' in snap);ck(not snap['response_grounding_learning']['raw_response_stored'])
print({'ok':all(checks),'passed':sum(checks),'total':len(checks)});raise SystemExit(0 if all(checks) else 1)
