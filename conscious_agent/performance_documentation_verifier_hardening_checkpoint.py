from __future__ import annotations
"""Read-only v1198.8 performance, documentation, and verifier reconciliation checkpoint."""
from pathlib import Path
from typing import Any
from performance_documentation_verifier_hardening import *
from performance_documentation_verifier_hardening import _digest
from checkpoint_registry import inspect_checkpoint_registry
CONTRACT_VERSION = "v1198.8"
CHECKPOINT_ID="performance-documentation-verifier-hardening-checkpoint"
def build_performance_documentation_verifier_hardening_checkpoint(*,source_root:str|Path|None=None,runtime_root:str|Path|None=None)->dict[str,Any]:
 d=lambda s:_digest(s);snap=d("1198.8:snapshot");ctx=d("1198.8:context");arch=d("1198.5:architecture");docs=d("1198.8:docs");reg=d("1198.8:registry");freeze=d("1198.5:review")
 p=create_hardening_plan(plan_id="v1198.8-hardening",snapshot_digest=snap,context_digest=ctx,architecture_digest=arch,documentation_digest=docs,verifier_registry_digest=reg,freeze_review_digest=freeze)
 rows=[];prior=""
 for i,c in enumerate(EVIDENCE_CLASSES,1):
  outcome="inherited_debt" if c=="fixture_overlap" else "pass";r=create_evidence(evidence_id=f"ev-{i}",evidence_class=c,outcome=outcome,owner="release-verification",sequence=i,observed_ms=100*i,budget_ms=1000*i,artifact_digest=d(c+":a"),receipt_digest=d(c+":r"),prior_receipt_digest=prior,debt_id="historical-fixture-overlap" if outcome=="inherited_debt" else "");rows.append(r);prior=r["receipt_digest"]
 a=assess_hardening(p,rows,current_snapshot_digest=snap,current_context_digest=ctx,current_architecture_digest=arch,current_documentation_digest=docs,current_verifier_registry_digest=reg,current_freeze_review_digest=freeze)
 source=Path(source_root) if source_root else Path(__file__).resolve().parents[1];registry=inspect_checkpoint_registry(source_root=source);desc=next((x for x in registry["checkpoints"] if x["checkpoint_id"]==CHECKPOINT_ID),None)
 checks=[a["status"]=="ready",a["evidence_count"]==8,a["evidence_class_count"]==8,a["inherited_debt_count"]==1,a["global_profile_pass_claimed"] is False,a["profiling_executed"] is False,a["verifier_executed"] is False,a["source_modified"] is False,a["runtime_mutated"] is False,a["authority_state"]=="separate_not_granted",bool(desc),(desc or {}).get("contract_version")==CONTRACT_VERSION,(desc or {}).get("read_only") is True,(desc or {}).get("post_available") is False]
 return {"ok":all(checks),"checkpoint_id":"performance-documentation-verifier-hardening:v1198.8","contract_version":CONTRACT_VERSION,"passed":sum(checks),"total":len(checks),"read_only":True,"post_available":False,"content_free":True,"evidence_class_count":8,"assessment":a,"global_profile_pass_claimed":False,"source_unchanged":True,"runtime_mutated":False,"profiling_executed":False,"verifier_executed":False,"files_moved":False,"files_deleted":False,"modules_merged":False,"imports_rewritten":False,"authority_granted":False}
