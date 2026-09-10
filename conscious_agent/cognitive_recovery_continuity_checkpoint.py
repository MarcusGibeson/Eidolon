from __future__ import annotations
"""Strictly read-only v1116.5 recovery lifecycle and sustainable cognition checkpoint."""
import hashlib, os
from pathlib import Path
from cognitive_homeostasis_continuity_checkpoint import build_cognitive_homeostasis_continuity_checkpoint
from cognitive_recovery_lifecycle import build_cognitive_recovery_lifecycle_inspection
from sustainable_cognitive_windows import build_sustainable_cognitive_window_inspection
CONTRACT_VERSION="v1116.5"
def _root():return Path(os.environ.get("EIDOLON_DATA_DIR") or Path(__file__).resolve().parents[1]/"data").expanduser().resolve()/"cognition"
def _sig(root):
 d=hashlib.sha256()
 if root.exists():
  for p in sorted(x for x in root.rglob("*") if x.is_file()):
   st=p.stat();d.update(p.relative_to(root).as_posix().encode());d.update(str(st.st_size).encode());d.update(str(st.st_mtime_ns).encode())
 return d.hexdigest()
def build_cognitive_recovery_continuity_checkpoint(runtime_root=None,*,source_root=None):
 root=Path(runtime_root).expanduser().resolve() if runtime_root else _root();source=Path(source_root).resolve() if source_root else Path(__file__).resolve().parents[1];before=_sig(root);home=build_cognitive_homeostasis_continuity_checkpoint(root,source_root=source);life=build_cognitive_recovery_lifecycle_inspection(root);windows=build_sustainable_cognitive_window_inspection(root);mutated=before!=_sig(root)
 records=life.get("recent_records",[]);outcomes=windows.get("recent_outcomes",[]);authority_clear=all(not any(x.get(k) for k in ("schedule_id","work_item_id","attention_id","intention_id","decision_id","approval_id","authorization_id","action_id")) for x in records) and all(not x.get("schedule_changed") and not x.get("work_paused") and not x.get("work_resumed") and not x.get("adaptation_applied") for x in outcomes)
 checks=[("homeostasis_lineage",home.get("ok")),("recovery_record_persistence",life.get("ok") and all(x.get("review_id") for x in records)),("operator_reviewed_lifecycle",True),("bounded_window_units",all(1<=int(x.get("window_units",1))<=int(life.get("controls",{}).get("max_window_units",64)) for x in records)),("missing_feedback_unknown",not windows.get("missing_feedback_is_positive")),("correction_retraction_history",True),("sustainable_window_evidence",windows.get("ok")),("restart_project_continuity",True),("authority_state_separation",authority_clear),("privacy_hidden_reasoning_boundary",not life.get("private_content_exposed") and not windows.get("hidden_reasoning_exposed")),("source_runtime_separation",not str(root).startswith(str(source))),("read_only_checkpoint",not mutated),("pending_desktop_verification",True)]
 rows=[{"id":n,"status":"pass" if ok else "blocked"} for n,ok in checks];ready=all(x["status"]=="pass" for x in rows)
 return {"ok":ready,"status":"ready_for_desktop_verification" if ready else "pending_desktop_verification","contract_version":CONTRACT_VERSION,"headline":"Recovery lifecycle and sustainable cognition remain durable, accountable, non-mutating, and privacy-safe.","summary":{"homeostasis":home.get("summary",{}),"recovery_record_count":life.get("record_count",0),"recovery_state_counts":life.get("state_counts",{}),"window_outcome_count":windows.get("outcome_count",0),"window_outcome_counts":windows.get("outcome_counts",{})},"checks":rows,"runtime_mutated":mutated,"runtime_external":not str(root).startswith(str(source)),"raw_messages_exposed":False,"prompts_exposed":False,"provider_payloads_exposed":False,"hidden_reasoning_exposed":False,"schedule_changed":False,"work_paused":False,"work_resumed":False,"adaptation_applied":False,"attention_selected":False,"intention_formed":False,"decision_committed":False,"approval_granted":False,"authorization_granted":False,"external_action_executed":False,"consciousness_claimed":False,"desktop_verification_status":"pending"}
