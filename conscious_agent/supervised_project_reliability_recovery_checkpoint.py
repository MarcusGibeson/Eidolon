from __future__ import annotations
"""Read-only v1184.8 adversarial reliability and recovery checkpoint."""
import hashlib
from pathlib import Path
from typing import Any
from checkpoint_registry import inspect_checkpoint_registry
from supervised_project_development_lineage import STAGES, create_project_stage_receipt, integrate_supervised_project_development
from supervised_project_outcome_learning import create_project_result_presentation, create_accountable_outcome_learning
from supervised_project_reliability_recovery import create_project_reliability_receipt, supervised_project_reliability_public_summary
CONTRACT_VERSION="v1184.8"
def _h(x:str)->str:return hashlib.sha256(x.encode()).hexdigest()
def build_supervised_project_reliability_recovery_checkpoint(*,source_root:str|Path|None=None,runtime_root:str|Path|None=None)->dict[str,Any]:
 source=Path(source_root or Path(__file__).resolve().parents[1]).resolve(); rows=[];prev="";checks=[]
 for s in STAGES:
  r=create_project_stage_receipt(stage=s,status="completed",artifact_digest=_h(s),previous_receipt_digest=prev,operator_review_digest=_h(s+":review"));rows.append(r);prev=r["receipt_digest"]
 lineage=integrate_supervised_project_development(rows)
 p=create_project_result_presentation(lineage=lineage,outcome="repaired",operator_decision_digest=_h("decision"),result_evidence_digest=_h("evidence"),rollback_available=True)
 l=create_accountable_outcome_learning(presentation=p,lesson_codes=["retain_repair_pattern"],operator_learning_review_digest=_h("learning"))
 good=create_project_reliability_receipt(lineage=lineage,presentation=p,learning=l,expected_source_digest=_h("source"),observed_source_digest=_h("source"),expected_terminal_digest=lineage["terminal_receipt_digest"],interruption_state="resumed",interruption_receipt_digest=_h("interrupt"),rollback_expected_digest=_h("rollback"),rollback_observed_digest=_h("rollback"))
 drift=create_project_reliability_receipt(lineage=lineage,presentation=p,learning=l,expected_source_digest=_h("source"),observed_source_digest=_h("changed"),expected_terminal_digest=lineage["terminal_receipt_digest"],interruption_state="resumed",interruption_receipt_digest=_h("interrupt"),rollback_expected_digest=_h("rollback"),rollback_observed_digest=_h("rollback"))
 privacy=create_project_reliability_receipt(lineage=lineage,presentation=p,learning=l,expected_source_digest=_h("source"),observed_source_digest=_h("source"),expected_terminal_digest=lineage["terminal_receipt_digest"],interruption_state="paused",interruption_receipt_digest=_h("interrupt"),rollback_expected_digest=_h("rollback"),rollback_observed_digest=_h("rollback"),privacy_findings=["private_content"])
 checks += [good["status"]=="recovery_review_ready",good["rollback_verified"] is True,drift["status"]=="blocked",drift["stale_source_detected"] is True,privacy["status"]=="blocked",good["authority_granted"] is False,good["rollback_executed"] is False]
 registry=inspect_checkpoint_registry(source_root=source);rr=next((x for x in registry["checkpoints"] if x["checkpoint_id"]=="supervised-project-reliability-recovery-checkpoint"),{})
 checks += [rr.get("builder")=="build_supervised_project_reliability_recovery_checkpoint",registry["duplicate_checkpoint_ids"]==[]]
 return {"ok":all(checks),"contract_version":CONTRACT_VERSION,"checkpoint_id":"supervised-project-reliability-recovery:v1184.8","passed":sum(checks),"total":len(checks),"read_only":True,"content_free":True,"summary":supervised_project_reliability_public_summary(good),"production_source_modified":False,"sandbox_modified":False,"execution_invoked":False,"provider_contacted":False,"model_contacted":False,"approval_created":False,"authority_granted":False,"release_authorized":False,"desktop_verification_deferred_until_v1200":True}
