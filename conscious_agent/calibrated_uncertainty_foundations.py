from __future__ import annotations
"""v1282.0-v1282.2 calibrated uncertainty foundations."""
import hashlib,json,re
from typing import Any,Mapping,Sequence
CONTRACT_VERSION="v1282.2";SCHEMA_VERSION="1";MAX_EVIDENCE=32;MAX_HISTORY=24
EPISTEMIC_STATES=("observed","inferred","assumed","unverified","suspended")
_SAFE=re.compile(r"^[a-z0-9][a-z0-9_.:-]{0,127}$")
AUTHORITY_FLAGS={"uncertainty_claim_is_execution_authority":False,"uncertainty_claim_is_provider_authority":False,"uncertainty_claim_is_test_authority":False,"uncertainty_claim_is_repair_authority":False,"uncertainty_claim_is_update_authority":False,"uncertainty_claim_is_application_authority":False,"uncertainty_claim_is_release_authority":False,"generic_approval_is_authorization":False,"permanent_approval_granted":False,"independent_authority_granted":False}
def _digest(v:Any)->str:return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=True,default=str).encode()).hexdigest()
def _code(v:Any,fallback="unknown"):
 t=str(v or "").strip().lower().replace(" ","_");t=re.sub(r"[^a-z0-9_.:-]+","_",t).strip("_")[:128];return t if t and _SAFE.fullmatch(t) else fallback
def confidence_band(score:int)->str:
 s=max(0,min(100,int(score)));return "very_low" if s<=20 else "low" if s<=40 else "medium" if s<=60 else "high" if s<=80 else "very_high" if s<=95 else "near_certain"
def _cap(state:str)->int:return {"observed":99,"inferred":80,"assumed":40,"unverified":20,"suspended":30}.get(state,20)
def build_uncertainty_claim(*,claim_code:str,epistemic_state:str,confidence:int,evidence_codes:Sequence[str]=(),contradiction_codes:Sequence[str]=(),freshness:str="current",history:Sequence[Mapping[str,Any]]=())->dict[str,Any]:
 state=_code(epistemic_state,"unverified");state=state if state in EPISTEMIC_STATES else "unverified";score=max(0,min(_cap(state),int(confidence)));e=[_code(x) for x in list(evidence_codes)[:MAX_EVIDENCE]];c=[_code(x) for x in list(contradiction_codes)[:MAX_EVIDENCE]];h=[dict(x) for x in list(history)[-MAX_HISTORY:]]
 row={"ok":True,"schema_version":SCHEMA_VERSION,"contract_version":CONTRACT_VERSION,"status":"calibrated_uncertainty_claim_ready","claim_code":_code(claim_code),"epistemic_state":state,"confidence":score,"confidence_band":confidence_band(score),"evidence_codes":e,"contradiction_codes":c,"freshness":_code(freshness,"unknown"),"history":h,"history_count":len(h),"confidence_is_evidence_responsive":True,"assumption_confidence_capped":True,"unknown_not_treated_as_false":True,"raw_content_stored":False,**AUTHORITY_FLAGS};row["claim_digest"]=_digest(row);return row
def validate_uncertainty_claim(row:Mapping[str,Any])->dict[str,Any]:
 expected=_digest({k:v for k,v in row.items() if k!="claim_digest"});digest=row.get("claim_digest")==expected;state=str(row.get("epistemic_state") or "");score=int(row.get("confidence") or 0);state_ok=state in EPISTEMIC_STATES and 0<=score<=_cap(state);band=row.get("confidence_band")==confidence_band(score);auth=all(row.get(k) is v for k,v in AUTHORITY_FLAGS.items());privacy=row.get("raw_content_stored") is False;hist=len(row.get("history") or [])<=MAX_HISTORY;ok=digest and state_ok and band and auth and privacy and hist
 return {"ok":ok,"status":"calibrated_uncertainty_claim_valid" if ok else "calibrated_uncertainty_claim_invalid","digest_valid":digest,"state_confidence_valid":state_ok,"band_valid":band,"authority_contained":auth,"privacy_contained":privacy,"history_bounded":hist}
def apply_uncertainty_evidence(claim:Mapping[str,Any],*,evidence_kind:str,evidence_code:str)->dict[str,Any]:
 if not validate_uncertainty_claim(claim).get("ok"):raise ValueError("valid_uncertainty_claim_required")
 kind=_code(evidence_kind);code=_code(evidence_code);e=list(claim.get("evidence_codes") or []);c=list(claim.get("contradiction_codes") or []);state=str(claim.get("epistemic_state"));score=int(claim.get("confidence") or 0);fresh=str(claim.get("freshness") or "unknown");duplicate=code in e or code in c
 before={"epistemic_state":state,"confidence":score,"freshness":fresh,"evidence_kind":kind,"evidence_code":code,"duplicate":duplicate}
 if not duplicate:
  if kind=="observed_support":e.append(code);state="observed";score=min(95,max(score,55)+20);fresh="current"
  elif kind=="observed_contradiction":c.append(code);score=max(0,score-50);state="suspended" if score<=40 else state;fresh="current"
  elif kind=="inferred_support":e.append(code);state="inferred" if state in {"assumed","unverified","suspended"} else state;score=min(_cap(state),score+12);fresh="current"
  elif kind=="assumption_context":e.append(code);state="assumed" if state in {"unverified","suspended"} else state;score=min(_cap(state),max(score,20));
  elif kind=="stale_evidence":c.append(code);score=max(0,score-25);state="unverified" if score<=20 else state;fresh="stale"
  elif kind=="evidence_retracted":c.append(code);score=max(0,score-30);state="suspended" if score<=30 else state
 hist=list(claim.get("history") or [])+[before];return build_uncertainty_claim(claim_code=str(claim.get("claim_code")),epistemic_state=state,confidence=score,evidence_codes=e,contradiction_codes=c,freshness=fresh,history=hist)
__all__=["CONTRACT_VERSION","EPISTEMIC_STATES","AUTHORITY_FLAGS","confidence_band","build_uncertainty_claim","validate_uncertainty_claim","apply_uncertainty_evidence"]
