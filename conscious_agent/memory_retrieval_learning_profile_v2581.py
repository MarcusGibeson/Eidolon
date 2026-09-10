from __future__ import annotations
"""v2581 longitudinal, advisory-only retrieval outcome profile."""
from typing import Any, Mapping, Sequence
import hashlib, json

CONTRACT_VERSION="v2581.0"
MIN_EVIDENCE=4

def _digest(v:Any)->str:return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":"),default=str).encode()).hexdigest()

def build_memory_retrieval_learning_profile(rows: Sequence[Mapping[str,Any]]) -> dict[str,Any]:
    bounded=[dict(r) for r in rows if isinstance(r,Mapping)][-96:]
    by_state={}
    for r in bounded:
        state=str(r.get("retrieval_state") or "unknown")[:48]
        bucket=by_state.setdefault(state,{"count":0,"positive":0,"negative":0,"restraint":0,"neutral":0,"corrections":0,"contradictions":0})
        bucket["count"]+=1
        disp=str(r.get("outcome_disposition") or "neutral_evidence")
        if disp=="positive_evidence":bucket["positive"]+=1
        elif disp=="negative_evidence":bucket["negative"]+=1
        elif disp=="appropriate_restraint":bucket["restraint"]+=1
        else:bucket["neutral"]+=1
        bucket["corrections"]+=int(bool(r.get("correction_detected")))
        bucket["contradictions"]+=int(bool(r.get("contradiction_detected")))
    profiles=[]
    for state,b in sorted(by_state.items()):
        n=b["count"]
        confidence=min(1.0,n/12.0)
        net=(b["positive"]+0.5*b["restraint"]-b["negative"])/max(1,n)
        if n<MIN_EVIDENCE: label="insufficient_evidence"
        elif net>=0.35: label="supportive_history"
        elif net<=-0.25: label="adverse_history"
        else: label="mixed_history"
        profiles.append({"retrieval_state":state,**b,"evidence_confidence":round(confidence,3),"net_outcome_score":round(net,3),"history_label":label})
    out={"ok":True,"contract_version":CONTRACT_VERSION,"observation_count":len(bounded),"profiles":profiles,"minimum_evidence":MIN_EVIDENCE,"retrieval_policy_mutated":False,"memory_mutated":False,"automatic_weight_change_permitted":False,"authority_granted":False,"raw_content_stored":False}
    out["profile_digest"]=_digest(out);return out

__all__=["CONTRACT_VERSION","build_memory_retrieval_learning_profile"]
