import json
from conscious_agent.response_grounding_policy_v2672 import build_response_grounding_policy,response_grounding_prompt_section
from conscious_agent.response_assertion_calibration_v2673 import build_response_assertion_calibration
checks=[]
sel={'selected_intent':'direct_answer','construction_directives':{'execution_claims_forbidden':True}}
for state,expected in [('grounded_relevant_memory','grounded'),('weak_context_only','cautious'),('no_useful_memory','cautious'),('grounded_correction','grounded')]:
 p=build_response_grounding_policy(sel,{'state':state,'should_preserve_uncertainty':state in {'weak_context_only','no_useful_memory'}},{});checks += [p['assertiveness']==expected,p['unsupported_memory_claims_forbidden'],not p['authority_granted']];c=build_response_assertion_calibration(p);checks += [c['must_not_invent_memory'],c['must_not_claim_execution_without_receipt'],not c['response_content_generated']]
p=build_response_grounding_policy(sel,{'state':'no_useful_memory','should_preserve_uncertainty':True},{'historical_uncertainty_required':True});text=response_grounding_prompt_section(p);checks += ['response_grounding' in text,'authority="none"' in text,'do not infer missing memories' in text]
print(json.dumps({'ok':all(checks),'passed':sum(checks),'total':len(checks)}));raise SystemExit(0 if all(checks) else 1)
