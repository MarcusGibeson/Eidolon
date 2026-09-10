from __future__ import annotations
"""Explicit private v1089.2 repair-candidate references; no patch execution."""
from datetime import datetime, timezone
import hashlib,json,uuid
from typing import Any,Mapping
from conversation_evaluation_finding import EvaluationFindingError, load_evaluation_finding_private, mutate_evaluation_finding
from conversation_evaluation_finding_reproducibility import build_finding_reproducibility
REFERENCE_KINDS=("patch_candidate","test_case","source_archive","external_work_item")
REFERENCE_STATES=("proposed","under_review","dismissed","superseded")
MAX_REPAIR_REFERENCES=24; MAX_REFERENCE_VALUE_CHARS=1000; MAX_REFERENCE_LABEL_CHARS=200

def _now(): return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00","Z")
def _digest(v:Any)->str: return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=True).encode()).hexdigest()
def _bounded(v:str,m:int,label:str,required=False)->str:
 t=str(v or "").strip()
 if required and not t: raise EvaluationFindingError(f"{label} is required.")
 if len(t)>m: raise EvaluationFindingError(f"{label} exceeds the {m}-character limit.")
 return t
def _public(row:Mapping[str,Any])->dict[str,Any]:
 value=str(row.get("private_reference_value") or ""); label=str(row.get("private_label") or "")
 return {"repair_reference_id":str(row.get("repair_reference_id") or ""),"reference_kind":str(row.get("reference_kind") or ""),"state":str(row.get("state") or "proposed"),"created_at":str(row.get("created_at") or ""),"updated_at":str(row.get("updated_at") or ""),"reference_present":bool(value),"reference_digest":_digest(value) if value else "","label_present":bool(label),"label_digest":_digest(label) if label else "","reproducibility_status_at_link":str(row.get("reproducibility_status_at_link") or "not_reviewed")}
def build_finding_repair_candidates(finding_id:str)->dict[str,Any]:
 r=load_evaluation_finding_private(finding_id); rows=[x for x in list(r.get("repair_candidate_refs") or []) if isinstance(x,Mapping)]; pub=[_public(x) for x in rows]; counts={k:0 for k in REFERENCE_STATES}
 for x in pub: counts[x["state"]]=counts.get(x["state"],0)+1
 return {"ok":True,"type":"desktop_alpha_evaluation_finding_repair_candidates","finding_id":str(r.get("finding_id") or ""),"finding_revision":int(r.get("revision") or 0),"reference_count":len(pub),"maximum_references":MAX_REPAIR_REFERENCES,"state_counts":counts,"references":pub,"references_digest":_digest(pub),"private_reference_values_returned":False,"private_labels_returned":False,"operator_confirmation_required":True,"optimistic_revision_required":True,"automatic_task_created":False,"automatic_work_item_created":False,"autonomous_prioritization":False,"patch_generated":False,"patch_reviewed":False,"patch_applied":False,"approval_granted":False,"rollback_authorized":False,"installation_performed":False,"promotion_performed":False,"release_certified":False,"provider_invoked":False,"writes_state":False,"content_free":True,"redacted":True}
def add_repair_candidate_reference(finding_id:str,*,reference_kind:str,reference_value:str,label:str="",expected_revision:int|None,operator_confirmed:bool)->dict[str,Any]:
 kind=str(reference_kind or "").strip().lower()
 if kind not in REFERENCE_KINDS: raise EvaluationFindingError("Unsupported repair-candidate reference kind.")
 value=_bounded(reference_value,MAX_REFERENCE_VALUE_CHARS,"Repair-candidate reference",True); private_label=_bounded(label,MAX_REFERENCE_LABEL_CHARS,"Repair-candidate label")
 repro=build_finding_reproducibility(finding_id)["reproducibility_status"]; duplicate={"value":False}
 class _Idempotent(Exception): pass
 def apply(r):
  rows=[x for x in list(r.get("repair_candidate_refs") or []) if isinstance(x,dict)]
  for x in rows:
   if str(x.get("reference_kind"))==kind and str(x.get("private_reference_value"))==value and str(x.get("state") or "proposed") in {"proposed","under_review"}: duplicate["value"]=True; raise _Idempotent
  if len(rows)>=MAX_REPAIR_REFERENCES: raise EvaluationFindingError("The finding has reached the repair-reference limit.")
  now=_now(); rows.append({"repair_reference_id":f"repair_ref_{uuid.uuid4().hex[:16]}","reference_kind":kind,"private_reference_value":value,"private_label":private_label,"state":"proposed","created_at":now,"updated_at":now,"reproducibility_status_at_link":repro}); r["repair_candidate_refs"]=rows
 try: mutate_evaluation_finding(finding_id,expected_revision=expected_revision,operator_confirmed=operator_confirmed,mutator=apply)
 except _Idempotent:
  result=build_finding_repair_candidates(finding_id); result["duplicate_reference"]=True; return result
 result=build_finding_repair_candidates(finding_id); result["duplicate_reference"]=False; return result
def update_repair_candidate_reference(finding_id:str,repair_reference_id:str,*,state:str,label:str|None=None,expected_revision:int|None,operator_confirmed:bool)->dict[str,Any]:
 token=str(repair_reference_id or "").strip(); state_token=str(state or "").strip().lower()
 if state_token not in REFERENCE_STATES: raise EvaluationFindingError("Unsupported repair-candidate reference state.")
 def apply(r):
  rows=[x for x in list(r.get("repair_candidate_refs") or []) if isinstance(x,dict)]; target=next((x for x in rows if str(x.get("repair_reference_id") or "")==token),None)
  if target is None: raise EvaluationFindingError("Repair-candidate reference not found.")
  target["state"]=state_token; target["updated_at"]=_now()
  if label is not None: target["private_label"]=_bounded(label,MAX_REFERENCE_LABEL_CHARS,"Repair-candidate label")
  r["repair_candidate_refs"]=rows
 mutate_evaluation_finding(finding_id,expected_revision=expected_revision,operator_confirmed=operator_confirmed,mutator=apply); return build_finding_repair_candidates(finding_id)
def remove_repair_candidate_reference(finding_id:str,repair_reference_id:str,*,expected_revision:int|None,operator_confirmed:bool)->dict[str,Any]:
 token=str(repair_reference_id or "").strip()
 def apply(r):
  rows=[x for x in list(r.get("repair_candidate_refs") or []) if isinstance(x,dict)]; kept=[x for x in rows if str(x.get("repair_reference_id") or "")!=token]
  if len(kept)==len(rows): raise EvaluationFindingError("Repair-candidate reference not found.")
  r["repair_candidate_refs"]=kept
 mutate_evaluation_finding(finding_id,expected_revision=expected_revision,operator_confirmed=operator_confirmed,mutator=apply); return build_finding_repair_candidates(finding_id)
