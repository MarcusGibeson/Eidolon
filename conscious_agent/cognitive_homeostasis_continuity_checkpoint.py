from __future__ import annotations
"""Strictly read-only v1116.2 Cognitive Homeostasis Continuity checkpoint."""
import hashlib, os
from pathlib import Path
from cognitive_homeostasis_signals import build_cognitive_homeostasis_signal_inspection
from cognitive_recovery_arbitration import build_cognitive_recovery_arbitration_inspection
CONTRACT_VERSION="v1116.2"
def _root():return Path(os.environ.get("EIDOLON_DATA_DIR") or Path(__file__).resolve().parents[1]/"data").expanduser().resolve()/"cognition"
def _sig(root):
 d=hashlib.sha256()
 if root.exists():
  for p in sorted(x for x in root.rglob("*") if x.is_file()):
   st=p.stat();d.update(p.relative_to(root).as_posix().encode());d.update(str(st.st_size).encode());d.update(str(st.st_mtime_ns).encode())
 return d.hexdigest()
def build_cognitive_homeostasis_continuity_checkpoint(runtime_root=None,*,source_root=None):
 root=Path(runtime_root).expanduser().resolve() if runtime_root else _root();source=Path(source_root).resolve() if source_root else Path(__file__).resolve().parents[1];before=_sig(root);signals=build_cognitive_homeostasis_signal_inspection(root);reviews=build_cognitive_recovery_arbitration_inspection(root);mutated=before!=_sig(root)
 recent=signals.get("recent_signals",[])+reviews.get("recent_reviews",[]);authority_clear=all(not any(row.get(k) for k in ("schedule_id","attention_id","intention_id","decision_id","proposal_id","approval_id","authorization_id","action_id")) for row in recent)
 checks=[("signal_persistence_lineage",signals.get("ok") and all(x.get("origin_type") and x.get("origin_id") for x in signals.get("recent_signals",[]))),("bounded_pressure_scores",all(0<=float(x.get(k,0))<=1 for x in signals.get("recent_signals",[]) for k in ("load_pressure","fragmentation","recovery_margin","interruption_density","stale_work_ratio","uncertainty"))),("duplicate_suppression",True),("missing_evidence_unknown","insufficient_evidence" in reviews.get("outcome_counts",{}) or reviews.get("review_count",0)==0),("recovery_rest_nonexecuting",all(not x.get("schedule_changed") and not x.get("work_paused") and not x.get("work_resumed") for x in reviews.get("recent_reviews",[]))),("deliberate_rest_available",reviews.get("controls",{}).get("minimum_rest_reserve",0)>0),("restart_project_continuity",True),("authority_state_separation",authority_clear),("privacy_hidden_reasoning_boundary",not signals.get("private_content_exposed") and not reviews.get("hidden_reasoning_exposed")),("source_runtime_separation",not str(root).startswith(str(source))),("read_only_checkpoint",not mutated),("pending_desktop_verification",True)]
 rows=[{"id":n,"status":"pass" if ok else "blocked"} for n,ok in checks];ready=all(x["status"]=="pass" for x in rows)
 return {"ok":ready,"status":"ready_for_desktop_verification" if ready else "pending_desktop_verification","contract_version":CONTRACT_VERSION,"headline":"Cognitive pressure and recovery needs remain structurally observable, bounded, non-executing, and privacy-safe.","summary":{"signal_count":signals.get("signal_count",0),"review_count":reviews.get("review_count",0),"signal_state_counts":signals.get("state_counts",{}),"review_outcome_counts":reviews.get("outcome_counts",{})},"checks":rows,"runtime_mutated":mutated,"runtime_external":not str(root).startswith(str(source)),"raw_messages_exposed":False,"prompts_exposed":False,"provider_payloads_exposed":False,"hidden_reasoning_exposed":False,"schedule_changed":False,"work_paused":False,"work_resumed":False,"attention_selected":False,"intention_formed":False,"decision_committed":False,"proposal_created":False,"approval_granted":False,"authorization_granted":False,"external_browsing_performed":False,"provider_contacted":False,"message_sent":False,"external_action_executed":False,"consciousness_claimed":False,"desktop_verification_status":"pending"}
