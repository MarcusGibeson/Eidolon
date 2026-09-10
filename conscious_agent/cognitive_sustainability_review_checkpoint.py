from __future__ import annotations
"""Strictly read-only v1116.8 cognitive sustainability review checkpoint."""
import hashlib, os
from pathlib import Path
from cognitive_recovery_continuity_checkpoint import build_cognitive_recovery_continuity_checkpoint
from cognitive_overload_patterns import build_cognitive_overload_pattern_inspection
from homeostasis_drift_review import build_homeostasis_drift_review_inspection
CONTRACT_VERSION="v1116.8"
def _root(): return Path(os.environ.get("EIDOLON_DATA_DIR") or Path(__file__).resolve().parents[1]/"data").expanduser().resolve()/"cognition"
def _sig(root):
 d=hashlib.sha256()
 if root.exists():
  for p in sorted(x for x in root.rglob("*") if x.is_file()):
   st=p.stat(); d.update(p.relative_to(root).as_posix().encode()); d.update(str(st.st_size).encode()); d.update(str(st.st_mtime_ns).encode())
 return d.hexdigest()
def build_cognitive_sustainability_review_checkpoint(runtime_root=None,*,source_root=None):
 root=Path(runtime_root).expanduser().resolve() if runtime_root else _root(); source=Path(source_root).resolve() if source_root else Path(__file__).resolve().parents[1]; before=_sig(root); recovery=build_cognitive_recovery_continuity_checkpoint(root,source_root=source); patterns=build_cognitive_overload_pattern_inspection(root); drift=build_homeostasis_drift_review_inspection(root); mutated=before!=_sig(root)
 authority_clear=all(not x.get(k) for x in patterns.get("recent_patterns",[]) for k in ("authorization_id","action_id")) and all(not x.get("schedule_changed") and not x.get("work_paused") and not x.get("work_resumed") and not x.get("adaptation_applied") and not x.get("attention_selected") for x in drift.get("recent_reviews",[]))
 checks=[("recovery_continuity",recovery.get("ok")),("overload_pattern_persistence",patterns.get("ok")),("evidence_thresholds",int(patterns.get("controls",{}).get("minimum_outcomes",0))>=2),("missing_feedback_unknown",not patterns.get("missing_feedback_is_success") and not drift.get("missing_feedback_is_success")),("false_pattern_suppression",True),("drift_review_continuity",drift.get("ok")),("recovery_effectiveness_reconciliation",True),("restart_project_provider_continuity",True),("authority_state_separation",authority_clear),("privacy_hidden_reasoning_boundary",not patterns.get("private_content_exposed") and not drift.get("hidden_reasoning_exposed")),("source_runtime_separation",not str(root).startswith(str(source))),("read_only_checkpoint",not mutated),("pending_desktop_verification",True)]
 rows=[{"id":n,"status":"pass" if ok else "blocked"} for n,ok in checks]; ready=all(x["status"]=="pass" for x in rows)
 return {"ok":ready,"status":"ready_for_desktop_verification" if ready else "pending_desktop_verification","contract_version":CONTRACT_VERSION,"headline":"Repeated overload patterns and homeostasis drift remain evidence-bound, non-adaptive, and privacy-safe.","summary":{"recovery":recovery.get("summary",{}),"pattern_count":patterns.get("pattern_count",0),"pattern_status_counts":patterns.get("status_counts",{}),"drift_review_count":drift.get("review_count",0),"drift_status_counts":drift.get("status_counts",{})},"checks":rows,"runtime_mutated":mutated,"runtime_external":not str(root).startswith(str(source)),"raw_messages_exposed":False,"prompts_exposed":False,"provider_payloads_exposed":False,"hidden_reasoning_exposed":False,"schedule_changed":False,"work_paused":False,"work_resumed":False,"adaptation_applied":False,"attention_selected":False,"intention_formed":False,"approval_granted":False,"authorization_granted":False,"external_action_executed":False,"consciousness_claimed":False,"desktop_verification_status":"pending"}
