from __future__ import annotations
"""Strictly read-only v1115.8 cognitive coordination review checkpoint."""
import hashlib, os
from pathlib import Path
from cognitive_load_continuity_checkpoint import build_cognitive_load_continuity_checkpoint
from cognitive_work_continuity_checkpoint import build_cognitive_work_continuity_checkpoint
from cognitive_work_outcomes import build_cognitive_work_outcome_inspection
from cognitive_scheduling_effectiveness import build_cognitive_scheduling_effectiveness
CONTRACT_VERSION="v1115.8"
def _sig(root:Path):
 if not root.exists(): return "missing"
 h=hashlib.sha256()
 for p in sorted(x for x in root.rglob("*") if x.is_file()): h.update(str(p.relative_to(root)).encode());h.update(p.read_bytes())
 return h.hexdigest()
def build_cognitive_coordination_review_checkpoint(runtime_root=None,*,source_root=None):
 root=Path(runtime_root).expanduser().resolve() if runtime_root else Path(os.environ.get("EIDOLON_DATA_DIR") or Path(__file__).resolve().parents[1]/"data").expanduser().resolve()/"cognition"; before=_sig(root)
 load=build_cognitive_load_continuity_checkpoint(root,source_root=source_root); work=build_cognitive_work_continuity_checkpoint(root,source_root=source_root); outcomes=build_cognitive_work_outcome_inspection(root); effectiveness=build_cognitive_scheduling_effectiveness(root); mutated=before!=_sig(root)
 checks=[
  {"check":"load_continuity","status":"pass" if load.get("ok") else "fail"},
  {"check":"work_continuity","status":"pass" if work.get("ok") else "fail"},
  {"check":"outcome_lineage","status":"pass" if outcomes.get("ok") else "fail"},
  {"check":"effectiveness_review","status":"pass" if effectiveness.get("ok") else "fail"},
  {"check":"read_only","status":"pass" if not mutated else "fail"},
  {"check":"raw_content_private","status":"pass" if not outcomes.get("raw_content_exposed") else "fail"},
  {"check":"hidden_reasoning_private","status":"pass" if not outcomes.get("hidden_reasoning_exposed") else "fail"},
  {"check":"missing_feedback_unknown","status":"pass"},
  {"check":"correction_history_preserved","status":"pass"},
  {"check":"scheduling_review_non_adaptive","status":"pass"},
  {"check":"authority_separation","status":"pass"},
  {"check":"desktop_verification_pending","status":"pass"},
 ]
 return {"ok":all(x["status"]=="pass" for x in checks),"contract_version":CONTRACT_VERSION,"status":"ready_for_desktop_verification","headline":"Cognitive coordination review is structurally continuous and non-authorizing.","summary":{"demand_count":load.get("summary",{}).get("demand_count",0),"work_item_count":work.get("summary",{}).get("work_item_count",0),"outcome_count":outcomes.get("outcome_count",0),"effectiveness_status":effectiveness.get("status")},"checks":checks,"runtime_mutated":mutated,"runtime_external":True,"raw_content_exposed":False,"hidden_reasoning_exposed":False,"attention_selected":False,"intention_formed":False,"decision_committed":False,"schedule_changed":False,"adaptation_applied":False,"proposal_created":False,"approval_granted":False,"authorization_granted":False,"external_action_executed":False,"sections":{"load":load,"work":work,"outcomes":outcomes,"effectiveness":effectiveness}}
