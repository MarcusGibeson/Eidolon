from __future__ import annotations
"""v1282.3-v1282.5 integration with causal and environment evidence."""
from typing import Any,Mapping
from calibrated_uncertainty_foundations import *
CONTRACT_VERSION="v1282.5"
def uncertainty_claim_from_causal_hypothesis(h:Mapping[str,Any])->dict[str,Any]:
 status=str(h.get("causal_status") or "unresolved");confidence=str(h.get("confidence") or "medium");base={"low":30,"medium":50,"high":70}.get(confidence,40)
 if status=="supported":state,score="inferred",min(80,base+15)
 elif status=="falsified":state,score="suspended",10
 else:state,score="unverified",20
 return build_uncertainty_claim(claim_code=f"causal_{h.get('hypothesis_code') or 'unknown'}",epistemic_state=state,confidence=score,evidence_codes=h.get("supporting_evidence") or [],contradiction_codes=h.get("contradicting_evidence") or [])
def uncertainty_claim_from_environment_fact(fact:Mapping[str,Any])->dict[str,Any]:
 raw=str(fact.get("epistemic_state") or fact.get("classification") or fact.get("evidence_class") or "unknown").lower();mapping={"observed":"observed","inferred":"inferred","assumed":"assumed","unknown":"unverified","unverified":"unverified"};state=mapping.get(raw,"unverified");base={"observed":85,"inferred":60,"assumed":30,"unverified":10}[state];fresh="stale" if fact.get("stale") is True or str(fact.get("freshness") or "") == "stale" else "current";claim=build_uncertainty_claim(claim_code=f"environment_{fact.get('fact_code') or fact.get('key') or 'fact'}",epistemic_state=state,confidence=base,evidence_codes=[str(fact.get("evidence_code") or raw)],freshness=fresh);return apply_uncertainty_evidence(claim,evidence_kind="stale_evidence",evidence_code="environment_fact_stale") if fresh=="stale" else claim
def calibrated_causal_claims(model:Mapping[str,Any])->dict[str,Any]:
 rows=[uncertainty_claim_from_causal_hypothesis(x) for x in model.get("hypotheses") or []];return {"ok":all(validate_uncertainty_claim(x).get("ok") for x in rows),"status":"calibrated_causal_claims_ready","claims":rows,"claim_count":len(rows),"root_cause_proven":False,"content_minimized":True,**AUTHORITY_FLAGS}
def public_uncertainty_summary(claim:Mapping[str,Any])->dict[str,Any]:
 v=validate_uncertainty_claim(claim);return {"ok":v.get("ok"),"claim_code":claim.get("claim_code"),"epistemic_state":claim.get("epistemic_state"),"confidence":claim.get("confidence"),"confidence_band":claim.get("confidence_band"),"freshness":claim.get("freshness"),"evidence_count":len(claim.get("evidence_codes") or []),"contradiction_count":len(claim.get("contradiction_codes") or []),"raw_content_exposed":False,**AUTHORITY_FLAGS}
__all__=["CONTRACT_VERSION","uncertainty_claim_from_causal_hypothesis","uncertainty_claim_from_environment_fact","calibrated_causal_claims","public_uncertainty_summary"]
