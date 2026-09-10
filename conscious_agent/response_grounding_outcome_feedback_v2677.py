from __future__ import annotations
"""v2677 explicit follow-up outcome evidence for response-grounding posture."""
from typing import Any, Mapping
import hashlib, json
CONTRACT_VERSION="v2677.0"
def _digest(v:Any)->str:return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":"),default=str).encode()).hexdigest()

def build_response_grounding_outcome_feedback(prior_observability:Mapping[str,Any], current_learning:Mapping[str,Any])->dict[str,Any]:
    prior=prior_observability.get("grounding") if isinstance(prior_observability.get("grounding"),Mapping) else {}
    candidate=current_learning.get("candidate") if isinstance(current_learning.get("candidate"),Mapping) else {}
    ctype=str(candidate.get("candidate_type") or "none")
    explicit_negative=ctype in {"correction","retraction"}
    present=bool(prior_observability.get("present")) and bool(prior)
    assertiveness=str(prior.get("assertiveness") or "unknown")
    if not present:
        disposition="no_prior_grounding_evidence"
    elif not explicit_negative:
        disposition="no_explicit_outcome_evidence"
    elif assertiveness=="grounded":
        disposition="grounded_claim_corrected"
    elif assertiveness=="current_turn_only":
        disposition="current_turn_claim_corrected"
    else:
        disposition="cautious_response_corrected"
    adverse=disposition in {"grounded_claim_corrected","current_turn_claim_corrected"}
    out={
        "ok":True,"contract_version":CONTRACT_VERSION,"evidence_recorded":bool(present and explicit_negative),
        "prior_assertiveness":assertiveness,"prior_memory_state":str(prior.get("memory_state") or "unknown")[:48],
        "explicit_correction":ctype=="correction","explicit_retraction":ctype=="retraction",
        "disposition":disposition,"adverse_calibration_evidence":adverse,
        "silence_treated_as_validation":False,"response_policy_mutated":False,"memory_policy_mutated":False,
        "raw_prompt_stored":False,"raw_response_stored":False,"raw_correction_text_stored":False,"authority_granted":False,
    }
    out["feedback_digest"]=_digest(out); return out
__all__=["CONTRACT_VERSION","build_response_grounding_outcome_feedback"]
