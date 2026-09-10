from __future__ import annotations
"""Content-free v1194 unified cognitive and developer experience contract."""
import hashlib, json
from typing import Any, Mapping, Sequence
CONTRACT_VERSION="v1194.2"
DOMAINS=("conversation","cognition","reasoning","planning","campaign","approval","action","result","learning")
WORK_SURFACES=("foreground","background")
PRIVATE_TOKENS=("prompt","message","memory","secret","source_text","patch_text","stdout","stderr","provider_payload","private_reasoning")

def _digest(value: object)->str:
 return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=True,default=str).encode()).hexdigest()
def _hex(value: object)->bool:
 token=str(value or "");return len(token)==64 and all(c in "0123456789abcdef" for c in token)
def _private(row: Mapping[str,Any])->list[str]:
 return sorted(k for k in row if any(t in str(k).lower() for t in PRIVATE_TOKENS))
def create_experience_record(*,domain:str,sequence:int,snapshot_digest:str,context_digest:str,artifact_digest:str,receipt_digest:str,purpose_code:str,foreground_available:bool=True,background_status:str="queued_not_running",approval_state:str="separate_not_consumed",execution_state:str="not_executed",authority_state:str="separate_not_granted",previous_record_digest:str="")->dict[str,Any]:
 row={"contract_version":CONTRACT_VERSION,"domain":domain,"sequence":sequence,"previous_record_digest":previous_record_digest,"snapshot_digest":snapshot_digest,"context_digest":context_digest,"artifact_digest":artifact_digest,"receipt_digest":receipt_digest,"purpose_code":purpose_code,"foreground_available":foreground_available,"background_status":background_status,"approval_state":approval_state,"execution_state":execution_state,"authority_state":authority_state,"content_free":True}
 row["record_digest"]=_digest(row);return row
def build_unified_view(records:Sequence[Mapping[str,Any]],*,current_snapshot_digest:str,current_context_digest:str,queue_summary:Mapping[str,Any],compaction_summary:Mapping[str,Any],verification_summary:Mapping[str,Any])->dict[str,Any]:
 errors=[]; rows=[dict(r) for r in records]
 if len(rows)!=9: errors.append("invalid_domain_count")
 if len(rows)>16: errors.append("oversized_input")
 if [r.get("sequence") for r in rows]!=list(range(len(rows))): errors.append("invalid_sequence")
 if len({r.get("domain") for r in rows})!=len(rows): errors.append("duplicate_domain")
 if set(r.get("domain") for r in rows)!=set(DOMAINS): errors.append("unsupported_or_missing_domain")
 previous=""
 for row in rows:
  private=_private(row)
  if private: errors.extend(f"private_field:{x}" for x in private)
  supplied=row.get("record_digest"); unsigned=dict(row);unsigned.pop("record_digest",None)
  if supplied!=_digest(unsigned): errors.append("record_tamper")
  if row.get("previous_record_digest")!=previous: errors.append("broken_lineage")
  previous=str(supplied or "")
  for field in ("snapshot_digest","context_digest","artifact_digest","receipt_digest"):
   if not _hex(row.get(field)): errors.append(f"malformed_{field}")
  if row.get("snapshot_digest")!=current_snapshot_digest: errors.append("stale_snapshot")
  if row.get("context_digest")!=current_context_digest: errors.append("stale_context")
  if row.get("foreground_available") is not True: errors.append("foreground_blocked")
  if row.get("background_status") not in {"none","proposed","review_required","queued_not_running","paused","completed","failed","blocked","cancelled","superseded"}: errors.append("unsupported_background_status")
  if row.get("approval_state")!="separate_not_consumed": errors.append("approval_boundary_loss")
  if row.get("execution_state")!="not_executed": errors.append("hidden_execution")
  if row.get("authority_state")!="separate_not_granted": errors.append("authority_expansion")
  if row.get("content_free") is not True: errors.append("content_exposure")
 for name,summary in (("queue",queue_summary),("compaction",compaction_summary),("verification",verification_summary)):
  if _private(summary): errors.append(f"private_{name}_summary")
  if summary.get("content_free") is not True: errors.append(f"invalid_{name}_summary")
 if queue_summary.get("foreground_path_available") is not True: errors.append("foreground_responsiveness_loss")
 if queue_summary.get("execution_invoked") is not False: errors.append("queue_execution_claim")
 if compaction_summary.get("original_evidence_preserved") is not True: errors.append("evidence_preservation_loss")
 if compaction_summary.get("exact_expansion_verified") is not True: errors.append("compaction_equivalence_loss")
 if verification_summary.get("current_regressions_separate") is not True: errors.append("verification_boundary_loss")
 if verification_summary.get("global_profile_pass_claimed") is not False: errors.append("global_pass_claim")
 summary={"contract_version":CONTRACT_VERSION,"domain_count":len(rows),"foreground_path_available":not any(x in errors for x in ("foreground_blocked","foreground_responsiveness_loss")),"background_work_separate":not any(x in errors for x in ("queue_execution_claim","hidden_execution")),"exact_expansion_verified":compaction_summary.get("exact_expansion_verified") is True,"original_evidence_preserved":compaction_summary.get("original_evidence_preserved") is True,"current_regressions_separate":verification_summary.get("current_regressions_separate") is True,"inherited_debt_visible":verification_summary.get("inherited_debt_visible") is True,"approval_separate":not any(x=="approval_boundary_loss" for x in errors),"execution_invoked":False,"runtime_mutated":False,"provider_contacted":False,"model_contacted":False,"authority_granted":False,"content_free":True}
 summary["unified_digest"]=_digest({"records":rows,"queue":dict(queue_summary),"compaction":dict(compaction_summary),"verification":dict(verification_summary),"summary":summary})
 return {"status":"ready_for_operator_view" if not errors else "blocked","errors":sorted(set(errors)),"error_count":len(set(errors)),"records":rows,"summary":summary,"execution_invoked":False,"runtime_mutated":False,"approval_consumed":False,"provider_contacted":False,"model_contacted":False,"thread_started":False,"process_started":False,"authority_granted":False}
def public_unified_summary(report:Mapping[str,Any])->dict[str,Any]: return dict(report.get("summary") or {})
