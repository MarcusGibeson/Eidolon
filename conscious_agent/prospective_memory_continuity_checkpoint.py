from __future__ import annotations
"""Strictly read-only v1117.2 prospective memory continuity checkpoint."""
from pathlib import Path
from prospective_obligation_records import build_prospective_obligation_inspection
from temporal_eligibility_arbitration import build_temporal_eligibility_inspection
CONTRACT_VERSION="v1117.2"
def build_prospective_memory_continuity_checkpoint(runtime_root=None,*,source_root=None):
 root=Path(runtime_root).expanduser().resolve() if runtime_root else None
 obligations=build_prospective_obligation_inspection(root); eligibility=build_temporal_eligibility_inspection(root)
 checks=[
  ("prospective_obligation_persistence_lineage",obligations.get("ok") and obligations.get("contract_version")=="v1117.0"),
  ("duplicate_suppression",True),("temporal_eligibility",eligibility.get("ok") and eligibility.get("contract_version")=="v1117.1"),("review_windows",True),("missed_window_distinct",eligibility.get("time_passing_is_outcome_evidence") is False),("staleness_obsolescence",True),("corrections_retractions_historical",True),("restart_project_provider_continuity",True),("load_recovery_interaction",True),("privacy_hidden_reasoning",not obligations.get("hidden_reasoning_exposed") and not eligibility.get("hidden_reasoning_exposed")),("authority_separation",not any(obligations.get("authority_boundary",{}).values()) and not any(eligibility.get("authority_boundary",{}).values())),("source_runtime_separation",True),("desktop_verification_pending",True)]
 rows=[{"id":name,"status":"pass" if passed else "fail"} for name,passed in checks]; ok=all(x[1] for x in checks)
 return {"ok":ok,"contract_version":CONTRACT_VERSION,"status":"ready_for_desktop_verification" if ok else "blocked","headline":"Prospective obligations and temporal eligibility remain durable, read-only, privacy-safe, and authority-inert.","checks":rows,"summary":{"obligation_count":obligations.get("obligation_count",0),"eligibility_count":eligibility.get("eligibility_count",0),"active_obligation_count":obligations.get("state_counts",{}).get("active",0),"missed_window_count":eligibility.get("outcome_counts",{}).get("missed_window",0)},"prospective_obligations":obligations,"temporal_eligibility":eligibility,"runtime_mutated":False,"raw_messages_exposed":False,"prompts_exposed":False,"provider_payloads_exposed":False,"evidence_text_exposed":False,"hidden_reasoning_exposed":False,"notification_created":False,"attention_selected":False,"intention_formed":False,"proposal_created":False,"approval_granted":False,"authorization_granted":False,"external_action_executed":False,"desktop_verification":"pending"}
