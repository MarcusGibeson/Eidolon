from __future__ import annotations
import json, sys, time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from conscious_agent.bounded_action_arguments import ARGUMENT_SCHEMAS, bind_bounded_action_arguments
from conscious_agent.natural_language_action_routing import build_natural_language_action_projection

checks=[]
def req(x): checks.append(bool(x)); assert x

def grounding(cid): return {"capability_id":cid}

r=bind_bounded_action_arguments("Run diagnostics", grounding("diagnostics")); req(r["binding_state"]=="bound"); req(r["argument_values"]=={"scope":"system"}); req(not r["authorization_inferred"] and not r["execution_performed"])
r=bind_bounded_action_arguments("Run provider diagnostics", grounding("diagnostics")); req(r["argument_values"]["scope"]=="provider")
r=bind_bounded_action_arguments("Review conscious_agent/memory.py", grounding("file_review")); req(r["argument_values"]["target_ref"]=="conscious_agent/memory.py")
r=bind_bounded_action_arguments("Review a file", grounding("file_review")); req(r["requires_clarification"] and r["missing_required"]==["target_ref"])
r=bind_bounded_action_arguments("Review x", grounding("file_review"), supplied_arguments={"target_ref":"../../bad secret"}); req(r["requires_clarification"] and "target_ref" in r["invalid_argument_names"])
r=bind_bounded_action_arguments("Run diagnostics", grounding("diagnostics"), supplied_arguments={"shell":"rm -rf /"}); req("shell" in r["unknown_argument_names"] and not r["exact_capability_argument_binding"])
r=bind_bounded_action_arguments("Do something", grounding("invented")); req(not r["registered_capability"] and r["requires_clarification"])
req(set(ARGUMENT_SCHEMAS)=={"diagnostics","maintenance","settings_health","approvals","task_project","memory","attention_center","notifications","planning","file_review","patch_proposal","self_development"})
req(r["receipt_bytes"]<=2048)
start=time.perf_counter()
for _ in range(1000): bind_bounded_action_arguments("Run runtime diagnostics", grounding("diagnostics"))
req((time.perf_counter()-start)<1.0)
p=build_natural_language_action_projection("Run diagnostics")
req(p["grounding"]["capability_id"]=="diagnostics")
req(not p["diagnostics"]["execution_performed"])
print(json.dumps({"ok":True,"suite":"v1176.0-v1176.2-bounded-action-argument-clarification-foundations","passed":sum(checks),"total":len(checks)},sort_keys=True))
