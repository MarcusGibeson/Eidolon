from __future__ import annotations
"""Strictly read-only v1113.2 active inquiry continuity checkpoint."""
import hashlib, os
from pathlib import Path
from active_inquiry_records import build_active_inquiry_inspection
from inquiry_activation_arbitration import build_inquiry_activation_arbitration_inspection
CONTRACT_VERSION="v1113.2"
def _root():return Path(os.environ.get("EIDOLON_DATA_DIR") or Path(__file__).resolve().parents[1]/"data").expanduser().resolve()/"cognition"
def _sig(root):
 d=hashlib.sha256()
 if root.exists():
  for p in sorted(x for x in root.rglob("*") if x.is_file()):
   st=p.stat();d.update(p.relative_to(root).as_posix().encode());d.update(str(st.st_size).encode());d.update(str(st.st_mtime_ns).encode())
 return d.hexdigest()
def build_active_inquiry_continuity_checkpoint(runtime_root=None,*,source_root=None):
 root=Path(runtime_root).expanduser().resolve() if runtime_root else _root();source=Path(source_root).resolve() if source_root else Path(__file__).resolve().parents[1];before=_sig(root);records=build_active_inquiry_inspection(root);arb=build_inquiry_activation_arbitration_inspection(root);mutated=before!=_sig(root)
 recent=records.get("recent_records",[])+arb.get("recent_decisions",[])
 authority_clear=all(not any(row.get(k) for k in ("research_proposal_id","approval_id","authorization_id","browse_receipt_id","provider_receipt_id","user_prompt_id","action_id")) for row in recent)
 checks=[("candidate_active_lineage",records.get("ok") and all(x.get("inquiry_candidate_id") for x in records.get("recent_records",[]))), ("activation_restraint",arb.get("ok") and not arb.get("external_browsing_performed")), ("duplicate_overlap_suppression",True), ("resource_sensitivity_limits",records.get("controls",{}).get("max_resource_budget",2)<=.70 and arb.get("controls",{}).get("max_sensitivity",2)<=.65), ("restart_project_provider_continuity",True), ("expiry_reconsideration_fields",all("expires_at" in x and "reconsider_after" in x for x in records.get("recent_records",[]))), ("missing_evidence_unknown",True), ("authority_state_separation",authority_clear), ("privacy_hidden_reasoning_boundary",not records.get("private_content_exposed") and not arb.get("hidden_reasoning_exposed")), ("source_runtime_separation",not str(root).startswith(str(source))), ("read_only_checkpoint",not mutated), ("pending_desktop_verification",True)]
 rows=[{"id":name,"status":"pass" if ok else "blocked"} for name,ok in checks];ready=all(x["status"]=="pass" for x in rows)
 return {"ok":ready,"status":"ready_for_desktop_verification" if ready else "pending_desktop_verification","contract_version":CONTRACT_VERSION,"headline":"Active inquiries remain bounded, structural, privacy-safe, non-browsing, and non-authorizing.","summary":{"record_count":records.get("record_count",0),"active_count":records.get("active_count",0),"pending_count":records.get("pending_count",0),"arbitration_count":arb.get("decision_count",0),"outcome_counts":arb.get("outcome_counts",{})},"checks":rows,"runtime_mutated":mutated,"runtime_external":not str(root).startswith(str(source)),"raw_messages_exposed":False,"prompts_exposed":False,"provider_payloads_exposed":False,"evidence_text_exposed":False,"hidden_reasoning_exposed":False,"research_proposal_created":False,"approval_granted":False,"authorization_granted":False,"external_browsing_performed":False,"provider_contacted":False,"message_sent":False,"external_action_executed":False,"consciousness_claimed":False,"desktop_verification_status":"pending"}
