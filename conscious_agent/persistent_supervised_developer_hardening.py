from __future__ import annotations
"""v1189.0-v1189.2 adversarial hardening foundations for the persistent supervised developer."""
import hashlib, json, re
from typing import Any, Mapping, Sequence
CONTRACT_VERSION="v1189.2"; SCHEMA_VERSION="1"; MAX_BYTES=262_144
DIGEST_RE=re.compile(r"^[0-9a-f]{64}$")
ALLOWED_OUTCOMES=frozenset({"completed","failed","blocked"})
FORBIDDEN_KEYS=frozenset({"raw_source","raw_patch","stdout","stderr","prompt","conversation","memory","secret","provider_payload","private_reasoning","authorization","approval_granted","release_authority"})
def _digest(v:object)->str:return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=True,default=str).encode()).hexdigest()
def _verify(row:Mapping[str,Any],field:str)->tuple[str,bool]:
 u=dict(row);d=str(u.pop(field,"")).lower();return d,bool(DIGEST_RE.fullmatch(d) and d==_digest(u))
def _bounded(v:object)->bool:return len(json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=True,default=str).encode())<=MAX_BYTES
def _forbidden(v:object)->bool:
 if isinstance(v,Mapping):
  return any(str(k).lower() in FORBIDDEN_KEYS or _forbidden(x) for k,x in v.items())
 if isinstance(v,(list,tuple)):return any(_forbidden(x) for x in v)
 return False

def create_supervised_developer_hardening_review(*,loop:Mapping[str,Any],result_receipt:Mapping[str,Any],reliability_receipt:Mapping[str,Any],learning_receipt:Mapping[str,Any],source_digest:str,expected_source_digest:str,review_nonce:str,seen_nonces:Sequence[str]=(),operator_review_digest:str="")->dict[str,Any]:
 l=dict(loop);r=dict(result_receipt);a=dict(reliability_receipt);n=dict(learning_receipt);errors=[]
 ld,lok=_verify(l,"loop_digest");rd,rok=_verify(r,"loop_result_receipt_digest");ad,aok=_verify(a,"loop_reliability_digest");nd,nok=_verify(n,"loop_learning_receipt_digest")
 if not lok:errors.append("tampered_loop")
 if not rok:errors.append("tampered_result")
 if not aok:errors.append("tampered_reliability")
 if not nok:errors.append("tampered_learning")
 if r.get("loop_digest")!=ld or a.get("loop_digest")!=ld or n.get("loop_digest")!=ld:errors.append("lineage_mismatch")
 if r.get("new_work_item_state") not in ALLOWED_OUTCOMES:errors.append("unsupported_outcome")
 current=str(source_digest).lower();expected=str(expected_source_digest).lower()
 if not DIGEST_RE.fullmatch(current) or not DIGEST_RE.fullmatch(expected):errors.append("invalid_source_digest")
 stale=current!=expected
 nonce=str(review_nonce or "")
 if not re.fullmatch(r"[A-Za-z0-9._:-]{8,128}",nonce):errors.append("invalid_review_nonce")
 if nonce in {str(x) for x in seen_nonces}:errors.append("replayed_review_nonce")
 od=str(operator_review_digest or "").lower()
 if not DIGEST_RE.fullmatch(od):errors.append("invalid_operator_review_digest")
 if _forbidden([l,r,a,n]):errors.append("private_or_authority_content_present")
 for row in (l,r,a,n):
  if row.get("content_free") is not True:errors.append("content_free_contract_violation")
  if any(row.get(k) is True for k in ("authority_granted","release_authorized","automatic_continuation","automatic_resume","learning_applied_to_policy","future_work_selection_modified")):errors.append("authority_expansion")
 if not _bounded([l,r,a,n]):errors.append("oversized_contract")
 errors=sorted(set(errors))
 out={"schema_version":SCHEMA_VERSION,"contract_version":CONTRACT_VERSION,"hardening_id":"persistent-supervised-developer-hardening:v1189.2","campaign_id":l.get("campaign_id",""),"work_item_id":l.get("work_item_id",""),"loop_digest":ld,"loop_result_receipt_digest":rd,"loop_reliability_digest":ad,"loop_learning_receipt_digest":nd,"source_digest":current,"expected_source_digest":expected,"source_stale":stale,"review_nonce":nonce,"operator_review_digest":od,"status":"operator_review_required" if not errors else "blocked","errors":errors,"error_count":len(errors),"content_free":True,"private_content_included":False,"replay_prevented":not errors,"production_source_modified":False,"sandbox_modified":False,"execution_invoked":False,"provider_contacted":False,"model_contacted":False,"automatic_retry":False,"automatic_resume":False,"automatic_continuation":False,"learning_applied_to_policy":False,"future_work_selection_modified":False,"authority_granted":False}
 out["hardening_receipt_digest"]=_digest(out);return out

def hardening_public_summary(row:Mapping[str,Any])->dict[str,Any]:
 return {"contract_version":CONTRACT_VERSION,"campaign_id":row.get("campaign_id",""),"work_item_id":row.get("work_item_id",""),"status":row.get("status",""),"source_stale":bool(row.get("source_stale")),"error_count":int(row.get("error_count",0) or 0),"hardening_receipt_digest":row.get("hardening_receipt_digest",""),"content_free":True,"authority_granted":False}
