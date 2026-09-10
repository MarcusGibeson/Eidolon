from __future__ import annotations
"""Read-only v1184.5 operator-facing results and accountable learning checkpoint."""
import hashlib
from pathlib import Path
from typing import Any
from checkpoint_registry import inspect_checkpoint_registry
from supervised_project_development_lineage import STAGES, create_project_stage_receipt, integrate_supervised_project_development
from supervised_project_outcome_learning import create_project_result_presentation, create_accountable_outcome_learning, project_outcome_public_summary
CONTRACT_VERSION="v1184.5"
def _h(x:str)->str:return hashlib.sha256(x.encode()).hexdigest()
def build_supervised_project_outcome_learning_checkpoint(*, source_root: str|Path|None=None, runtime_root: str|Path|None=None)->dict[str,Any]:
    source=Path(source_root or Path(__file__).resolve().parents[1]).resolve(); checks=[]
    rows=[]; prev=""
    for stage in STAGES:
        row=create_project_stage_receipt(stage=stage,status="completed",artifact_digest=_h(stage),previous_receipt_digest=prev,operator_review_digest=_h(stage+":review"));rows.append(row);prev=row["receipt_digest"]
    lineage=integrate_supervised_project_development(rows)
    presentations=[]; learnings=[]
    codes={"accepted":["retain_approach"],"rejected":["avoid_rejected_approach"],"failed":["strengthen_failure_checks"],"repaired":["retain_repair_pattern"]}
    for outcome in codes:
        p=create_project_result_presentation(lineage=lineage,outcome=outcome,operator_decision_digest=_h(outcome+":decision"),result_evidence_digest=_h(outcome+":evidence"),rollback_available=outcome in {"failed","repaired"})
        l=create_accountable_outcome_learning(presentation=p,lesson_codes=codes[outcome],operator_learning_review_digest=_h(outcome+":learning-review"))
        checks += [p["status"]=="ready_for_operator_review", l["status"]=="learning_recorded", p["authority_granted"] is False, l["historical_truth_preserved"] is True]
        presentations.append(p);learnings.append(l)
    bad=dict(presentations[0]);bad["outcome"]="failed"
    checks.append(create_accountable_outcome_learning(presentation=bad,lesson_codes=["strengthen_failure_checks"],operator_learning_review_digest=_h("x"))["status"]=="blocked")
    checks.append(create_accountable_outcome_learning(presentation=presentations[0],lesson_codes=["retain_approach","retain_approach"],operator_learning_review_digest=_h("x"))["status"]=="blocked")
    registry=inspect_checkpoint_registry(source_root=source); row=next((x for x in registry["checkpoints"] if x["checkpoint_id"]=="supervised-project-outcome-learning-checkpoint"),{})
    checks += [row.get("builder")=="build_supervised_project_outcome_learning_checkpoint", registry["duplicate_checkpoint_ids"]==[]]
    return {"ok":all(checks),"contract_version":CONTRACT_VERSION,"checkpoint_id":"supervised-project-outcome-learning:v1184.5","passed":sum(checks),"total":len(checks),"read_only":True,"content_free":True,"summaries":[project_outcome_public_summary(p,l) for p,l in zip(presentations,learnings)],"production_source_modified":False,"sandbox_modified":False,"execution_invoked":False,"provider_contacted":False,"model_contacted":False,"approval_created":False,"authority_granted":False,"release_authorized":False,"desktop_verification_deferred_until_v1200":True}
