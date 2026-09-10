from __future__ import annotations
"""v2582 read-only retrieval-policy learning advisories."""
from typing import Any, Mapping
import hashlib,json
CONTRACT_VERSION="v2582.0"
def _digest(v:Any)->str:return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":"),default=str).encode()).hexdigest()
def build_memory_retrieval_learning_advisory(profile:Mapping[str,Any])->dict[str,Any]:
    items=[]
    for row in profile.get("profiles") or []:
        if not isinstance(row,Mapping):continue
        label=str(row.get("history_label") or "insufficient_evidence")
        state=str(row.get("retrieval_state") or "unknown")
        if label=="adverse_history": recommendation="review_precision_for_state"
        elif label=="supportive_history": recommendation="retain_current_policy"
        elif label=="mixed_history": recommendation="collect_more_outcome_evidence"
        else: recommendation="insufficient_evidence_no_change"
        items.append({"retrieval_state":state,"history_label":label,"recommendation":recommendation,"evidence_confidence":float(row.get("evidence_confidence") or 0.0),"policy_change_permitted":False})
    out={"ok":True,"contract_version":CONTRACT_VERSION,"advisories":items,"automatic_policy_change_permitted":False,"score_mutation_performed":False,"memory_mutation_performed":False,"provider_contacted":False,"operator_review_required_for_policy_change":True,"authority_granted":False}
    out["advisory_digest"]=_digest(out);return out
__all__=["CONTRACT_VERSION","build_memory_retrieval_learning_advisory"]
