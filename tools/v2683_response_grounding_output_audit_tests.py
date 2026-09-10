from conscious_agent.response_grounding_output_audit_v2683 import audit_response_grounding_output
p={'personal_memory_reference_permitted':False}; c={'must_not_claim_execution_without_receipt':True}
checks=[]
def ck(x): checks.append(bool(x))
a=audit_response_grounding_output('I remember you told me that already.',p,c);ck(not a['ok']);ck(a['memory_claim_shape_count']>0);ck(not a['response_rewritten']);ck(not a['raw_response_stored'])
b=audit_response_grounding_output('I think this is probably the right answer.',p,c);ck(b['ok'])
e=audit_response_grounding_output('I installed the update.',p,c);ck(not e['ok']);ck(e['execution_claim_shape_count']==1)
e2=audit_response_grounding_output('I installed the update.',p,c,authoritative_execution_evidence=True);ck(e2['ok']);ck(not e2['authority_granted'])
print({'ok':all(checks),'passed':sum(checks),'total':len(checks)});raise SystemExit(0 if all(checks) else 1)
