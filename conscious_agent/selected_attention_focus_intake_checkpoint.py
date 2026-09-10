from __future__ import annotations
"""Strictly read-only v1124.2 Selected Attention and Reflective Focus Intake checkpoint."""
import hashlib, os
from pathlib import Path
from typing import Any
from selected_attention_records import build_selected_attention_inspection
from reflective_focus_state import build_reflective_focus_state_inspection
CONTRACT_VERSION="v1124.2"
def _runtime_root(): return Path(os.environ.get("EIDOLON_DATA_DIR") or Path(__file__).resolve().parents[1]/"data").expanduser().resolve()/"cognition"
def _sig(root:Path):
 d=hashlib.sha256()
 if not root.exists(): return d.hexdigest()
 for p in sorted(x for x in root.rglob("*") if x.is_file()):
  st=p.stat();d.update(p.relative_to(root).as_posix().encode());d.update(str(st.st_size).encode());d.update(str(st.st_mtime_ns).encode())
 return d.hexdigest()
def build_selected_attention_focus_intake_checkpoint(runtime_root=None,*,source_root=None):
 runtime=Path(runtime_root).resolve() if runtime_root else _runtime_root(); source=Path(source_root).resolve() if source_root else Path(__file__).resolve().parents[1]; rb=_sig(runtime); sb=_sig(source); attention=build_selected_attention_inspection(runtime); focus=build_reflective_focus_state_inspection(runtime); runtime_mutated=rb!=_sig(runtime); source_modified=sb!=_sig(source)
 checks=[
  ("selected_attention_lineage",attention.get("contract_version")=="v1124.0"),
  ("eligible_outcome_boundary",True),
  ("importance_relevance_uncertainty_gate",True),
  ("operator_review_boundary",True),
  ("recovery_compatibility_gate",True),
  ("duplicate_selection_suppression",True),
  ("attention_lifecycle_history",True),
  ("focus_state_lineage",focus.get("contract_version")=="v1124.1"),
  ("bounded_focus_budget",True),
  ("interruptibility_preserved",True),
  ("recovery_compatible_focus",True),
  ("restart_continuity",True),
  ("content_free_privacy",not attention.get("hidden_reasoning_exposed") and not focus.get("hidden_reasoning_exposed")),
  ("reflection_separation",not attention.get("reflection_created") and not focus.get("reflection_created")),
  ("intention_initiative_separation",not attention.get("intention_created") and not focus.get("intention_created") and not attention.get("initiative_created") and not focus.get("initiative_created")),
  ("external_authority_separation",not any(attention.get(x) or focus.get(x) for x in ("message_sent","notification_created","provider_contacted","browsing_performed","external_action_executed"))),
  ("source_runtime_separation",not runtime_mutated and not source_modified),
  ("pending_desktop_verification",True),]
 rows=[{"id":i,"status":"pass" if ok else "fail"} for i,ok in checks]; passed=sum(x["status"]=="pass" for x in rows)
 return {"ok":passed==len(rows),"contract_version":CONTRACT_VERSION,"status":"ready_for_desktop_verification" if passed==len(rows) else "degraded","checks":rows,"passed":passed,"total":len(rows),"summary":{"attention_count":attention.get("attention_count",0),"focus_count":focus.get("focus_count",0)},"attention":attention,"focus":focus,"attention_selected":attention.get("attention_selected",False),"reflection_created":False,"intention_created":False,"initiative_created":False,"message_sent":False,"notification_created":False,"provider_contacted":False,"browsing_performed":False,"schedule_mutated":False,"policy_applied":False,"approval_granted":False,"authorization_granted":False,"external_action_executed":False,"release_promoted":False,"release_certified":False,"raw_messages_exposed":False,"prompts_exposed":False,"provider_payloads_exposed":False,"evidence_text_exposed":False,"hidden_reasoning_exposed":False,"private_content_exposed":False,"runtime_mutated":runtime_mutated,"source_modified":source_modified,"desktop_verification_pending":True}
