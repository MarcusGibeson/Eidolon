from __future__ import annotations
"""Strictly read-only v1111.8 curiosity lifecycle checkpoint."""
import hashlib, os
from pathlib import Path
from curiosity_inquiry_promotion import build_curiosity_inquiry_promotion_inspection
from curiosity_question_lifecycle import build_curiosity_question_lifecycle_inspection
CONTRACT_VERSION="v1111.8"
def _root():return Path(os.environ.get("EIDOLON_DATA_DIR") or Path(__file__).resolve().parents[1]/"data").expanduser().resolve()/"cognition"
def _sig(root):
 if not root.exists():return hashlib.sha256(b"").hexdigest()
 rows=[]
 for p in sorted(x for x in root.rglob("*") if x.is_file()):
  st=p.stat();rows.append(f"{p.relative_to(root)}:{st.st_size}:{st.st_mtime_ns}")
 return hashlib.sha256("\n".join(rows).encode()).hexdigest()
def _inside(p,q):
 try:p.resolve().relative_to(q.resolve());return True
 except ValueError:return False
def build_curiosity_lifecycle_checkpoint(runtime_root=None,*,source_root=None):
 root=Path(runtime_root).expanduser().resolve() if runtime_root else _root();source=Path(source_root).resolve() if source_root else Path(__file__).resolve().parents[1];before=_sig(root);p=build_curiosity_inquiry_promotion_inspection(root);l=build_curiosity_question_lifecycle_inspection(root);after=_sig(root);checks={"promotion_lineage":p.get("contract_version")=="v1111.6","lifecycle_lineage":l.get("contract_version")=="v1111.7","runtime_immutable":before==after,"provider_neutral":not p.get("provider_contacted") and not l.get("provider_contacted"),"no_browsing":not p.get("external_browsing_performed") and not l.get("external_browsing_performed"),"no_message":not p.get("message_sent") and not l.get("message_sent"),"privacy":not p.get("private_content_exposed") and not l.get("private_content_exposed"),"authority_separation":all(not any((r.get("active_inquiry_id"),r.get("browse_receipt_id"),r.get("user_prompt_id"),r.get("proposal_id"),r.get("authorization_id"),r.get("action_id"))) for r in p.get("recent_promotions",[])+l.get("recent_decisions",[]))};status="ready_for_desktop_verification" if all(checks.values()) else "needs_review";return {"ok":all(checks.values()),"contract_version":CONTRACT_VERSION,"status":status,"summary":{"promotion_count":p.get("promotion_count",0),"active_candidate_count":p.get("active_candidate_count",0),"lifecycle_decision_count":l.get("decision_count",0),"outcome_counts":l.get("outcome_counts",{})},"checks":checks,"check_count":len(checks),"runtime_external":not _inside(root,source),"runtime_mutated":False,"source_modified":False,"provider_contacted":False,"external_browsing_performed":False,"message_sent":False,"external_action_executed":False,"hidden_reasoning_exposed":False,"private_content_exposed":False,"action_authority_changed":False,"desktop_verification_required":True,"desktop_verification_status":"pending","consciousness_claimed":False}
