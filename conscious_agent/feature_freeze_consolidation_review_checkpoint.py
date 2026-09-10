from __future__ import annotations
"""Read-only v1198.5 operator freeze-exception and consolidation review checkpoint."""
import hashlib, copy
from pathlib import Path
from typing import Any
from checkpoint_registry import inspect_checkpoint_registry
from feature_freeze_consolidation_review import REVIEW_ACTIONS, DECISIONS, create_review_request, review_freeze_or_consolidation, public_review_summary, _digest
from package_integrity import package_privacy_summary_for_root
CONTRACT_VERSION = "v1198.5"
def _d(value: str) -> str: return hashlib.sha256(value.encode("utf-8")).hexdigest()

def build_feature_freeze_consolidation_review_checkpoint(*, source_root: str | Path | None = None, runtime_root: str | Path | None = None) -> dict[str, Any]:
    source = Path(source_root or Path(__file__).resolve().parents[1]).resolve(); del runtime_root
    checks: list[bool] = []
    def require(value: object) -> None: checks.append(bool(value))
    snapshot, context, assessment, architecture = (_d("v1198.5:snapshot"), _d("v1198.5:context"), _d("v1198.2:assessment"), _d("v1198.2:architecture"))
    reviews: list[dict[str, Any]] = []; prior = ""; seq = 1
    for action in REVIEW_ACTIONS:
        for decision in DECISIONS:
            req = create_review_request(request_id=f"{action}-{decision}", action=action, snapshot_digest=snapshot, context_digest=context, assessment_digest=assessment, architecture_digest=architecture, target_id=f"target-{action}", sequence=seq, prior_review_receipt_digest=prior, purpose_code="operator_freeze_consolidation_review")
            result = review_freeze_or_consolidation(req, decision=decision, operator_review_digest=_d(f"operator:{action}:{decision}"), current_snapshot_digest=snapshot, current_context_digest=context, current_assessment_digest=assessment, current_architecture_digest=architecture, expected_sequence=seq, expected_prior_review_receipt_digest=prior)
            require(result["status"] == "reviewed"); require(not result["errors"])
            require(result["presentation_outcome"] in ("eligible_for_separate_application_review", "rejected", "deferred"))
            require(result["separate_application_review_required"] is (decision == "approve"))
            summary = public_review_summary(result)
            for field in ("exception_applied", "files_moved", "modules_merged", "files_deleted", "imports_rewritten", "startup_executed", "runtime_mutated", "source_modified", "approval_created", "approval_consumed", "provider_contacted", "model_contacted", "process_started", "thread_started", "installation_performed", "promotion_performed", "certification_performed", "publication_performed", "release_performed", "automatic_continuation"):
                require(summary[field] is False)
            require(summary["authority_state"] == "separate_not_granted")
            reviews.append(summary); prior = result["review_receipt_digest"]; seq += 1
    base = create_review_request(request_id="blocked", action="freeze_exception", snapshot_digest=snapshot, context_digest=context, assessment_digest=assessment, architecture_digest=architecture, target_id="target", sequence=1, prior_review_receipt_digest="", purpose_code="operator_freeze_consolidation_review")
    blocked: dict[str, list[str]] = {}
    mutations = {"stale-snapshot":("snapshot_digest",_d("stale")),"stale-context":("context_digest",_d("stale")),"stale-assessment":("assessment_digest",_d("stale")),"stale-architecture":("architecture_digest",_d("stale")),"unsupported-action":("action","delete_source"),"private-field":("secret","redacted"),"exception-applied":("exception_applied",True),"files-moved":("files_moved",True),"module-merge":("modules_merged",True),"files-deleted":("files_deleted",True),"imports-rewritten":("imports_rewritten",True),"startup-executed":("startup_executed",True),"approval-consumed":("approval_consumed",True),"provider-contact":("provider_contacted",True),"process-start":("process_started",True),"release":("release_performed",True),"automatic":("automatic_continuation",True),"authority":("authority_state","granted")}
    for name,(field,value) in mutations.items():
        req=copy.deepcopy(base); req[field]=value; req["request_digest"]=_digest({k:v for k,v in req.items() if k!="request_digest"})
        out=review_freeze_or_consolidation(req, decision="approve", operator_review_digest=_d("operator"), current_snapshot_digest=snapshot, current_context_digest=context, current_assessment_digest=assessment, current_architecture_digest=architecture, expected_sequence=1, expected_prior_review_receipt_digest="")
        require(out["status"]=="blocked"); require(bool(out["errors"])); blocked[name]=out["errors"]
    for name, kwargs in {"bad-decision":{"decision":"apply"},"bad-operator-digest":{"operator_review_digest":"bad"},"bad-sequence":{"expected_sequence":2},"bad-lineage":{"expected_prior_review_receipt_digest":_d("prior")}}.items():
        params={"decision":"approve","operator_review_digest":_d("operator"),"current_snapshot_digest":snapshot,"current_context_digest":context,"current_assessment_digest":assessment,"current_architecture_digest":architecture,"expected_sequence":1,"expected_prior_review_receipt_digest":""}; params.update(kwargs)
        out=review_freeze_or_consolidation(base, **params); require(out["status"]=="blocked"); require(bool(out["errors"])); blocked[name]=out["errors"]
    privacy=package_privacy_summary_for_root(source); require(privacy.get("ok") is True)
    registry=inspect_checkpoint_registry(source_root=source); descriptor=next((row for row in registry["checkpoints"] if row["checkpoint_id"]=="feature-freeze-consolidation-review-checkpoint"),None)
    require(bool(descriptor)); require((descriptor or {}).get("contract_version")==CONTRACT_VERSION); require((descriptor or {}).get("builder")=="build_feature_freeze_consolidation_review_checkpoint"); require((descriptor or {}).get("read_only") is True); require((descriptor or {}).get("post_available") is False)
    return {"ok":all(checks),"checkpoint_id":"feature-freeze-consolidation-review:v1198.5","contract_version":CONTRACT_VERSION,"passed":sum(checks),"total":len(checks),"read_only":True,"post_available":False,"content_free":True,"review_count":len(reviews),"action_count":len(REVIEW_ACTIONS),"decision_count":len(DECISIONS),"reviews":reviews,"blocked_cases":blocked,"source_unchanged":True,"runtime_mutated":False,"files_moved":False,"modules_merged":False,"files_deleted":False,"imports_rewritten":False,"startup_executed":False,"exception_applied":False,"approval_created":False,"approval_consumed":False,"provider_contacted":False,"model_contacted":False,"process_started":False,"thread_started":False,"installation_performed":False,"promotion_performed":False,"certification_performed":False,"publication_performed":False,"release_performed":False,"automatic_continuation":False,"authority_granted":False,"privacy":privacy,"limitations":["Review outcomes are presentation-only; no freeze exception or consolidation change is applied.","No file move, merge, deletion, import rewrite, or startup profiling occurs.","Approved outcomes require a separate future application review.","No installation, promotion, certification, publication, release, or autonomous authority is granted."]}
