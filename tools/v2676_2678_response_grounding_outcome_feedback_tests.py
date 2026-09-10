from pathlib import Path
import tempfile
from conscious_agent.response_grounding_observability_v2676 import *
from conscious_agent.response_grounding_outcome_feedback_v2677 import *
from conscious_agent.response_grounding_learning_profile_v2678 import *
checks=[]
def ck(x): checks.append(bool(x))
with tempfile.TemporaryDirectory() as td:
 p={"assertiveness":"cautious","memory_state":"weak_context_only","preserve_uncertainty":True,"personal_memory_reference_permitted":False,"policy_digest":"a"*64}
 c={"assertion_level":"explicit_uncertainty","calibration_digest":"b"*64}
 r=record_response_grounding_observability(p,c,operation_id="turn-1",runtime_root=td); l=load_response_grounding_observability(td)
 ck(r["present"] and l["present"]); ck(not l["grounding"].get("raw_prompt_stored") and not l["grounding"].get("raw_response_stored") and not l["grounding"].get("raw_memory_text_stored")); ck(not l["authority_granted"])
prior={"present":True,"grounding":{"assertiveness":"grounded","memory_state":"grounded_relevant_memory"}}
neg=build_response_grounding_outcome_feedback(prior,{"candidate":{"candidate_type":"correction"}}); ck(neg["evidence_recorded"]); ck(neg["adverse_calibration_evidence"])
neutral=build_response_grounding_outcome_feedback(prior,{"candidate":{"candidate_type":"none"}}); ck(not neutral["evidence_recorded"]); ck(not neutral["silence_treated_as_validation"])
caut=build_response_grounding_outcome_feedback({"present":True,"grounding":{"assertiveness":"cautious"}},{"candidate":{"candidate_type":"correction"}}); ck(not caut["adverse_calibration_evidence"])
profile=build_response_grounding_learning_profile([neg,neg,neg]); ck(profile["state"]=="overassertion_review_due"); ck(not profile["automatic_policy_change"])
review=build_response_grounding_policy_review(profile); ck(review["review_due"]); ck(not review["response_policy_mutated"]); ck(not review["authority_granted"])
print({"ok":all(checks),"passed":sum(checks),"total":len(checks)})
raise SystemExit(0 if all(checks) else 1)
