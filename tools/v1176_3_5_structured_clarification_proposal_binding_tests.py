from __future__ import annotations
import json, sys, time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"conscious_agent"))
from natural_language_action_routing import build_natural_language_action_projection, natural_language_action_public_projection
from structured_action_clarification import (
    build_structured_clarification_request,
    apply_structured_clarification_answer,
    build_clarified_proposal_binding,
)

checks=[]
def req(v): checks.append(bool(v)); assert v

p=build_natural_language_action_projection("Review a file")
r=build_structured_clarification_request(p)
req(r["state"]=="awaiting_structured_answer")
req(r["requested_fields"]==["target_ref"])
req(not r["persisted"] and r["authority_state"]=="not_granted")
req("clarification_request" in natural_language_action_public_projection(p))

a=apply_structured_clarification_answer(p,r,{"target_ref":"conscious_agent/memory.py"})
req(a["state"]=="bound" and a["exact_clarified_binding"])
req(a["binding"]["argument_values"]=={"target_ref":"conscious_agent/memory.py"})
req(a["request_consumed"] and not a["approval_created"] and not a["execution_performed"])

b=build_clarified_proposal_binding(p,a,operation_id="review-memory")
req(b["proposal_binding"]["state"]=="ready_for_separate_persistence")
req(b["proposal_binding"]["exact_digest_binding"])
req(b["proposal_binding"]["proposal_candidate_created"])
req(not b["proposal_binding"]["proposal_persisted"] and not b["proposal_binding"]["approval_created"])
req(not b["proposal_binding"]["execution_admitted"] and not b["proposal_binding"]["execution_performed"])

replay=apply_structured_clarification_answer(p,r,{"target_ref":"conscious_agent/memory.py"},consumed_request_digests=[r["request_digest"]])
req(replay["state"]=="replayed" and not replay["proposal_binding_eligible"])

stale=dict(r); stale["source_projection_digest"]="0"*64
st=apply_structured_clarification_answer(p,stale,{"target_ref":"conscious_agent/memory.py"})
req(st["state"]=="stale_or_mismatched" and not st["request_verified"])

bad=apply_structured_clarification_answer(p,r,{"target_ref":"../../secret","shell":"rm"})
req(not bad["exact_clarified_binding"] and "shell" in bad["unknown_answer_fields"])

missing=apply_structured_clarification_answer(p,r,{})
req(not missing["exact_clarified_binding"])

q=build_natural_language_action_projection("Run diagnostics")
qr=build_structured_clarification_request(q)
req(qr["state"]=="not_required" and qr["requested_fields"]==[])

start=time.perf_counter()
for _ in range(1000):
    apply_structured_clarification_answer(p,r,{"target_ref":"conscious_agent/memory.py"})
req(time.perf_counter()-start < 1.5)
req(len(json.dumps(b,sort_keys=True).encode()) < 4096)
req("conscious_agent/memory.py" not in json.dumps(r,sort_keys=True))

print(json.dumps({"ok":True,"suite":"v1176.3-v1176.5-structured-clarification-proposal-binding-integration","passed":sum(checks),"total":len(checks)},sort_keys=True))
