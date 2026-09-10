import tempfile
from conscious_agent.response_grounding_output_audit_v2683 import audit_response_grounding_output
from conscious_agent.response_grounding_audit_observability_v2686 import record_response_grounding_output_audit,load_response_grounding_output_audit_observability
from conscious_agent.response_grounding_repair_candidate_v2687 import build_response_grounding_repair_candidate
from conscious_agent.response_grounding_repair_review_v2688 import build_response_grounding_repair_review
checks=[]
def ck(x):checks.append(bool(x))
p={'personal_memory_reference_permitted':False,'policy_digest':'a'*64};c={'must_not_claim_execution_without_receipt':True,'calibration_digest':'b'*64};a=audit_response_grounding_output('I remember you said this and I installed it.',p,c)
with tempfile.TemporaryDirectory() as td:
 r=record_response_grounding_output_audit(a,operation_id='op',runtime_root=td);o=load_response_grounding_output_audit_observability(td);ck(o['concern_event_count']==1);ck(not o['raw_response_stored']);ck(not o['authority_granted'])
cand=build_response_grounding_repair_candidate(a,p,c);ck(cand['state']=='repair_candidate_ready');ck(len(cand['action_codes'])==2);ck(not cand['response_rewritten']);ck(not cand['automatic_regeneration'])
rev=build_response_grounding_repair_review(cand);ck(rev['review_required']);ck(not rev['automatic_response_rewrite']);ck(not rev['automatic_provider_regeneration']);ck(not rev['authority_granted'])
print({'ok':all(checks),'passed':sum(checks),'total':len(checks)});raise SystemExit(0 if all(checks) else 1)
