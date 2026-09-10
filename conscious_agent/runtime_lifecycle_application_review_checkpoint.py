from __future__ import annotations

"""Read-only v1197.5 operator-reviewed runtime lifecycle application checkpoint."""

import hashlib
from pathlib import Path
from typing import Any

from checkpoint_registry import inspect_checkpoint_registry
from package_integrity import package_privacy_summary_for_root
from runtime_lifecycle_application_review import DECISIONS, REASON_CODES, REVIEW_ACTIONS, REVIEW_ACTION_BY_OPERATION, build_lifecycle_application_review_decision, build_lifecycle_application_review_request, public_lifecycle_application_review_summary, review_runtime_lifecycle_application
from runtime_lifecycle_migration import LIFECYCLE_OPERATIONS, _digest

CONTRACT_VERSION = "v1197.5"
_CHECKPOINT_ID = "runtime-lifecycle-application-review-checkpoint"


def _h(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def build_runtime_lifecycle_application_review_checkpoint(
    *, source_root: str | Path | None = None, runtime_root: str | Path | None = None
) -> dict[str, Any]:
    source = Path(source_root or Path(__file__).resolve().parents[1]).resolve()
    del runtime_root
    checks: list[bool] = []

    def require(value: object) -> None:
        checks.append(bool(value))

    lifecycle_id = "runtime-lifecycle:v1197.5"
    snapshot = _h("v1197.5:snapshot")
    context = _h("v1197.5:context")
    plan = _h("v1197.5:plan")
    assessment = _h("v1197.5:assessment")
    previous = ""
    samples: list[dict[str, Any]] = []

    for sequence, operation in enumerate(LIFECYCLE_OPERATIONS, 1):
        evidence = _h(f"v1197.5:evidence:{operation}")
        request = build_lifecycle_application_review_request(
            review_id=f"lifecycle-review:{sequence}", lifecycle_id=lifecycle_id,
            operation=operation, sequence=sequence, snapshot_digest=snapshot,
            context_digest=context, plan_digest=plan, evidence_digest=evidence,
            assessment_digest=assessment, previous_review_receipt_digest=previous,
            purpose_code=f"operator_{operation}_application_review",
        )
        for decision_name in DECISIONS:
            decision = build_lifecycle_application_review_decision(
                request_digest=request["request_digest"], decision=decision_name,
                operator_review_digest=_h(f"operator:{operation}:{decision_name}"),
                reason_code={"approve": "evidence_sufficient", "reject": "evidence_rejected", "defer": "more_evidence_required"}[decision_name],
            )
            result = review_runtime_lifecycle_application(
                request=request, decision=decision, expected_lifecycle_id=lifecycle_id,
                expected_operation=operation, expected_sequence=sequence,
                expected_snapshot_digest=snapshot, expected_context_digest=context,
                expected_plan_digest=plan, expected_evidence_digest=evidence,
                expected_assessment_digest=assessment,
                expected_previous_review_receipt_digest=previous,
            )
            require(result["ok"] is True)
            require(not result["errors"])
            require(result["operation_executed"] is False)
            require(result["application_authorized"] is False)
            require(result["authority_granted"] is False)
            samples.append(result)
        previous = samples[-1]["review_receipt_digest"]

    base_operation = "migration"
    base_evidence = _h("negative:evidence")
    base_request = build_lifecycle_application_review_request(
        review_id="negative-review", lifecycle_id=lifecycle_id, operation=base_operation,
        sequence=2, snapshot_digest=snapshot, context_digest=context, plan_digest=plan,
        evidence_digest=base_evidence, assessment_digest=assessment,
        previous_review_receipt_digest="", purpose_code="negative_review",
    )
    base_decision = build_lifecycle_application_review_decision(
        request_digest=base_request["request_digest"], decision="approve",
        operator_review_digest=_h("negative:operator"), reason_code="evidence_sufficient",
    )

    request_mutations = (
        ("stale-snapshot", "snapshot_digest", _h("stale")),
        ("stale-context", "context_digest", _h("stale")),
        ("stale-plan", "plan_digest", _h("stale")),
        ("stale-evidence", "evidence_digest", _h("stale")),
        ("stale-assessment", "assessment_digest", _h("stale")),
        ("wrong-operation", "operation", "upgrade"),
        ("unsupported-action", "action", "apply_now"),
        ("wrong-sequence", "sequence", 4),
        ("runtime-read", "runtime_read", True),
        ("backup-created", "backup_created", True),
        ("migration-applied", "migration_applied", True),
        ("upgrade-applied", "upgrade_applied", True),
        ("rollback-applied", "rollback_applied", True),
        ("fresh-install", "fresh_install_performed", True),
        ("files-written", "files_written", True),
        ("files-deleted", "files_deleted", True),
        ("runtime-mutated", "runtime_mutated", True),
        ("source-modified", "source_modified", True),
        ("provider-contact", "provider_contacted", True),
        ("model-contact", "model_contacted", True),
        ("thread-start", "thread_started", True),
        ("process-start", "process_started", True),
        ("approval-created", "approval_created", True),
        ("approval-consumed", "approval_consumed", True),
        ("automatic-continuation", "automatic_continuation", True),
        ("application-authority", "application_authority_requested", True),
        ("authority", "authority_state", "granted"),
        ("private-field", "secret", "forbidden"),
    )
    decision_mutations = (
        ("unsupported-decision", "decision", "execute"),
        ("request-mismatch", "request_digest", _h("wrong-request")),
        ("bad-operator-digest", "operator_review_digest", "bad"),
        ("unsupported-reason", "reason_code", "because"),
        ("operation-executed", "operation_executed", True),
        ("decision-runtime-read", "runtime_read", True),
        ("decision-files-written", "files_written", True),
        ("decision-files-deleted", "files_deleted", True),
        ("decision-runtime-mutated", "runtime_mutated", True),
        ("decision-source-modified", "source_modified", True),
        ("decision-provider", "provider_contacted", True),
        ("decision-model", "model_contacted", True),
        ("decision-thread", "thread_started", True),
        ("decision-process", "process_started", True),
        ("decision-approval-created", "approval_created", True),
        ("decision-approval-consumed", "approval_consumed", True),
        ("decision-continuation", "automatic_continuation", True),
        ("application-authorized", "application_authorized", True),
        ("authority-granted", "authority_granted", True),
        ("decision-private", "private_reasoning", "forbidden"),
    )
    blocked: dict[str, list[str]] = {}
    for name, field, value in request_mutations:
        request = dict(base_request)
        request[field] = value
        body = dict(request); body.pop("request_digest", None)
        request["request_digest"] = _digest(body)
        decision = build_lifecycle_application_review_decision(
            request_digest=request["request_digest"], decision="approve",
            operator_review_digest=_h("negative:operator"), reason_code="evidence_sufficient",
        )
        result = review_runtime_lifecycle_application(
            request=request, decision=decision, expected_lifecycle_id=lifecycle_id,
            expected_operation=base_operation, expected_sequence=2,
            expected_snapshot_digest=snapshot, expected_context_digest=context,
            expected_plan_digest=plan, expected_evidence_digest=base_evidence,
            expected_assessment_digest=assessment,
            expected_previous_review_receipt_digest="",
        )
        require(result["ok"] is False); require(bool(result["errors"])); require(result["operation_executed"] is False); require(result["authority_granted"] is False)
        blocked[name] = result["errors"]
    for name, field, value in decision_mutations:
        decision = dict(base_decision)
        decision[field] = value
        body = dict(decision); body.pop("decision_digest", None)
        decision["decision_digest"] = _digest(body)
        result = review_runtime_lifecycle_application(
            request=base_request, decision=decision, expected_lifecycle_id=lifecycle_id,
            expected_operation=base_operation, expected_sequence=2,
            expected_snapshot_digest=snapshot, expected_context_digest=context,
            expected_plan_digest=plan, expected_evidence_digest=base_evidence,
            expected_assessment_digest=assessment,
            expected_previous_review_receipt_digest="",
        )
        require(result["ok"] is False); require(bool(result["errors"])); require(result["operation_executed"] is False); require(result["authority_granted"] is False)
        blocked[name] = result["errors"]

    summary = public_lifecycle_application_review_summary(samples)
    require(summary["review_count"] == len(LIFECYCLE_OPERATIONS) * len(DECISIONS))
    require(summary["operation_count"] == len(LIFECYCLE_OPERATIONS))
    require(summary["decision_count"] == len(DECISIONS))
    require(summary["all_reviews_valid"] is True)
    for field in ("content_free", "presentation_only", "exact_lineage_verified", "original_runtime_preserved", "backup_truth_preserved", "rollback_truth_preserved", "fresh_install_isolation_preserved", "separate_application_authorization_required"):
        require(summary[field] is True)
    for field in ("runtime_read", "backup_created", "migration_applied", "upgrade_applied", "rollback_applied", "fresh_install_performed", "files_written", "files_deleted", "runtime_mutated", "source_modified", "provider_contacted", "model_contacted", "thread_started", "process_started", "approval_created", "approval_consumed", "automatic_continuation", "application_authorized", "operation_executed", "global_profile_pass_claimed", "authority_granted"):
        require(summary[field] is False)

    privacy = package_privacy_summary_for_root(source)
    require(privacy.get("ok") is True)
    registry = inspect_checkpoint_registry(source_root=source)
    descriptor = next((row for row in registry["checkpoints"] if row["checkpoint_id"] == _CHECKPOINT_ID), None)
    require(descriptor is not None)
    require((descriptor or {}).get("contract_version") == CONTRACT_VERSION)
    require((descriptor or {}).get("builder") == "build_runtime_lifecycle_application_review_checkpoint")
    require((descriptor or {}).get("read_only") is True)
    require((descriptor or {}).get("post_available") is False)

    return {
        "ok": all(checks),
        "checkpoint_id": "runtime-lifecycle-application-review:v1197.5",
        "contract_version": CONTRACT_VERSION,
        "passed": sum(checks),
        "total": len(checks),
        "read_only": True,
        "post_available": False,
        "content_free": True,
        "source_unchanged": True,
        "runtime_mutated": False,
        "production_source_modified": False,
        "runtime_read": False,
        "backup_created": False,
        "migration_applied": False,
        "upgrade_applied": False,
        "rollback_applied": False,
        "fresh_install_performed": False,
        "files_written": False,
        "files_deleted": False,
        "approval_created": False,
        "approval_consumed": False,
        "provider_contacted": False,
        "model_contacted": False,
        "thread_started": False,
        "process_started": False,
        "automatic_continuation": False,
        "application_authorized": False,
        "operation_executed": False,
        "global_profile_pass_claimed": False,
        "authority_granted": False,
        "summary": summary,
        "samples": samples,
        "blocked_cases": blocked,
        "limitations": [
            "Review outcomes are presentation-only and do not apply lifecycle operations.",
            "No runtime data is read, copied, migrated, upgraded, restored, or installed.",
            "No approval or application authority is created or consumed.",
            "No provider, model, process, thread, source, or runtime mutation occurs.",
            "Reliability, interruption, stale-state, and rollback adversarial hardening continues in v1197.6-v1197.8.",
        ],
    }
