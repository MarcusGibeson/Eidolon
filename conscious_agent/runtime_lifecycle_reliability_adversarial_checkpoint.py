from __future__ import annotations

"""Read-only v1197.8 Runtime Lifecycle Reliability checkpoint."""

import hashlib
from pathlib import Path
from typing import Any

from checkpoint_registry import inspect_checkpoint_registry
from package_integrity import package_privacy_summary_for_root
from runtime_lifecycle_reliability_adversarial import EVENT_CLASSES, OPERATIONS, _digest, build_runtime_lifecycle_reliability_event, inspect_runtime_lifecycle_reliability_event, public_runtime_lifecycle_reliability_summary

CONTRACT_VERSION = "v1197.8"
_CHECKPOINT_ID = "runtime-lifecycle-reliability-adversarial-checkpoint"


def _h(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def build_runtime_lifecycle_reliability_adversarial_checkpoint(
    *, source_root: str | Path | None = None, runtime_root: str | Path | None = None
) -> dict[str, Any]:
    source = Path(source_root or Path(__file__).resolve().parents[1]).resolve()
    del runtime_root
    checks: list[bool] = []

    def require(value: object) -> None:
        checks.append(bool(value))

    lifecycle_id = "runtime-lifecycle:v1197.8"
    snapshot = _h("v1197.8:snapshot")
    context = _h("v1197.8:context")
    plan = _h("v1197.8:plan")
    assessment = _h("v1197.8:assessment")
    application_review = _h("v1197.8:application-review")
    source_runtime = _h("v1197.8:source-runtime")
    backup = _h("v1197.8:backup")
    rollback = _h("v1197.8:rollback")
    manifest = _h("v1197.8:manifest")
    previous = ""
    samples: list[dict[str, Any]] = []
    metrics = {
        "stale_runtime_state": {"integrity_failure_count": 1},
        "backup_integrity_failure": {"integrity_failure_count": 2},
        "migration_interruption": {"interruption_count": 1},
        "upgrade_interruption": {"interruption_count": 2},
        "rollback_failure": {"rollback_failure_count": 1},
        "fresh_install_contamination": {"contamination_finding_count": 1},
        "schema_compatibility_drift": {"schema_drift_score": 15},
        "recovery_reentry": {"recovery_reentry_count": 2},
    }
    operation_by_event = {
        "stale_runtime_state": "backup",
        "backup_integrity_failure": "backup",
        "migration_interruption": "migration",
        "upgrade_interruption": "upgrade",
        "rollback_failure": "rollback",
        "fresh_install_contamination": "fresh_install",
        "schema_compatibility_drift": "upgrade",
        "recovery_reentry": "rollback",
    }

    for sequence, event_class in enumerate(EVENT_CLASSES, 1):
        operation = operation_by_event[event_class]
        event = build_runtime_lifecycle_reliability_event(
            event_id=f"lifecycle-reliability:{sequence}", lifecycle_id=lifecycle_id,
            event_class=event_class, operation=operation, sequence=sequence,
            snapshot_digest=snapshot, context_digest=context, plan_digest=plan,
            evidence_digest=_h(f"v1197.8:evidence:{operation}"), assessment_digest=assessment,
            application_review_receipt_digest=application_review,
            source_runtime_digest=source_runtime, backup_digest=backup,
            rollback_digest=rollback, manifest_digest=manifest,
            artifact_digest=_h(f"v1197.8:artifact:{sequence}"),
            receipt_digest=_h(f"v1197.8:receipt:{sequence}"),
            previous_event_receipt_digest=previous,
            foreground_latency_ms=sequence * 5, latency_budget_ms=250,
            **metrics[event_class],
        )
        result = inspect_runtime_lifecycle_reliability_event(
            event=event, expected_lifecycle_id=lifecycle_id,
            expected_operation=operation, expected_sequence=sequence,
            expected_snapshot_digest=snapshot, expected_context_digest=context,
            expected_plan_digest=plan,
            expected_evidence_digest=_h(f"v1197.8:evidence:{operation}"),
            expected_assessment_digest=assessment,
            expected_application_review_receipt_digest=application_review,
            expected_source_runtime_digest=source_runtime,
            expected_backup_digest=backup, expected_rollback_digest=rollback,
            expected_manifest_digest=manifest,
            expected_previous_event_receipt_digest=previous,
        )
        for value in (
            result["ok"], not result["errors"], result["exact_lineage_verified"],
            result["original_runtime_preserved"], result["backup_truth_preserved"],
            result["rollback_truth_preserved"], result["existing_runtime_untouched"],
            result["foreground_available"], result["recovery_review_required"],
        ):
            require(value)
        for field in (
            "runtime_read", "backup_created", "migration_applied", "upgrade_applied",
            "rollback_applied", "fresh_install_performed", "files_written", "files_deleted",
            "automatic_recovery", "automatic_retry", "provider_contacted", "model_contacted",
            "thread_started", "process_started", "approval_created", "approval_consumed",
            "runtime_mutated", "source_modified", "global_profile_pass_claimed", "authority_granted",
        ):
            require(result[field] is False)
        samples.append(result)
        previous = result["reliability_receipt_digest"]

    base = build_runtime_lifecycle_reliability_event(
        event_id="negative", lifecycle_id=lifecycle_id,
        event_class="backup_integrity_failure", operation="backup", sequence=1,
        snapshot_digest=snapshot, context_digest=context, plan_digest=plan,
        evidence_digest=_h("v1197.8:evidence:backup"), assessment_digest=assessment,
        application_review_receipt_digest=application_review,
        source_runtime_digest=source_runtime, backup_digest=backup,
        rollback_digest=rollback, manifest_digest=manifest,
        artifact_digest=_h("negative:artifact"), receipt_digest=_h("negative:receipt"),
        integrity_failure_count=1, foreground_latency_ms=1, latency_budget_ms=250,
    )
    mutations = (
        ("stale-lifecycle", "lifecycle_id", "stale"),
        ("stale-snapshot", "snapshot_digest", _h("stale")),
        ("stale-context", "context_digest", _h("stale")),
        ("stale-plan", "plan_digest", _h("stale")),
        ("stale-evidence", "evidence_digest", _h("stale")),
        ("stale-assessment", "assessment_digest", _h("stale")),
        ("stale-review", "application_review_receipt_digest", _h("stale")),
        ("stale-runtime", "source_runtime_digest", _h("stale")),
        ("stale-backup", "backup_digest", _h("stale")),
        ("stale-rollback", "rollback_digest", _h("stale")),
        ("stale-manifest", "manifest_digest", _h("stale")),
        ("unsupported-event", "event_class", "apply_now"),
        ("unsupported-operation", "operation", "delete_runtime"),
        ("wrong-sequence", "sequence", 2),
        ("latency", "foreground_latency_ms", 251),
        ("foreground-block", "foreground_available", False),
        ("runtime-loss", "original_runtime_preserved", False),
        ("backup-truth-loss", "backup_truth_preserved", False),
        ("rollback-truth-loss", "rollback_truth_preserved", False),
        ("runtime-touched", "existing_runtime_untouched", False),
        ("runtime-read", "runtime_read", True),
        ("backup-created", "backup_created", True),
        ("migration-applied", "migration_applied", True),
        ("upgrade-applied", "upgrade_applied", True),
        ("rollback-applied", "rollback_applied", True),
        ("fresh-install", "fresh_install_performed", True),
        ("files-written", "files_written", True),
        ("files-deleted", "files_deleted", True),
        ("recovery", "automatic_recovery", True),
        ("retry", "automatic_retry", True),
        ("provider", "provider_contacted", True),
        ("model", "model_contacted", True),
        ("thread", "thread_started", True),
        ("process", "process_started", True),
        ("approval-created", "approval_created", True),
        ("approval-consumed", "approval_consumed", True),
        ("runtime-mutated", "runtime_mutated", True),
        ("source-modified", "source_modified", True),
        ("global-pass", "global_profile_pass_claimed", True),
        ("authority", "authority_granted", True),
        ("authority-state", "authority_state", "granted"),
        ("private-field", "secret", "forbidden"),
    )
    blocked: dict[str, list[str]] = {}
    for name, field, value in mutations:
        event = dict(base)
        event[field] = value
        unsigned = dict(event)
        unsigned.pop("event_digest", None)
        event["event_digest"] = _digest(unsigned)
        result = inspect_runtime_lifecycle_reliability_event(
            event=event, expected_lifecycle_id=lifecycle_id,
            expected_operation="backup", expected_sequence=1,
            expected_snapshot_digest=snapshot, expected_context_digest=context,
            expected_plan_digest=plan,
            expected_evidence_digest=_h("v1197.8:evidence:backup"),
            expected_assessment_digest=assessment,
            expected_application_review_receipt_digest=application_review,
            expected_source_runtime_digest=source_runtime,
            expected_backup_digest=backup, expected_rollback_digest=rollback,
            expected_manifest_digest=manifest,
        )
        require(result["ok"] is False)
        require(bool(result["errors"]))
        require(result["runtime_mutated"] is False)
        require(result["authority_granted"] is False)
        blocked[name] = result["errors"]

    tampered = dict(base)
    tampered["operation"] = "migration"
    tamper_result = inspect_runtime_lifecycle_reliability_event(
        event=tampered, expected_lifecycle_id=lifecycle_id,
        expected_operation="backup", expected_sequence=1,
        expected_snapshot_digest=snapshot, expected_context_digest=context,
        expected_plan_digest=plan,
        expected_evidence_digest=_h("v1197.8:evidence:backup"),
        expected_assessment_digest=assessment,
        expected_application_review_receipt_digest=application_review,
        expected_source_runtime_digest=source_runtime,
        expected_backup_digest=backup, expected_rollback_digest=rollback,
        expected_manifest_digest=manifest,
    )
    require(tamper_result["ok"] is False)
    require("event_tamper" in tamper_result["errors"])
    blocked["tamper"] = tamper_result["errors"]

    broken = build_runtime_lifecycle_reliability_event(
        event_id="broken", lifecycle_id=lifecycle_id,
        event_class="migration_interruption", operation="migration", sequence=2,
        snapshot_digest=snapshot, context_digest=context, plan_digest=plan,
        evidence_digest=_h("v1197.8:evidence:migration"), assessment_digest=assessment,
        application_review_receipt_digest=application_review,
        source_runtime_digest=source_runtime, backup_digest=backup,
        rollback_digest=rollback, manifest_digest=manifest,
        artifact_digest=_h("broken:artifact"), receipt_digest=_h("broken:receipt"),
        previous_event_receipt_digest=_h("wrong-prior"), interruption_count=1,
    )
    broken_result = inspect_runtime_lifecycle_reliability_event(
        event=broken, expected_lifecycle_id=lifecycle_id,
        expected_operation="migration", expected_sequence=2,
        expected_snapshot_digest=snapshot, expected_context_digest=context,
        expected_plan_digest=plan,
        expected_evidence_digest=_h("v1197.8:evidence:migration"),
        expected_assessment_digest=assessment,
        expected_application_review_receipt_digest=application_review,
        expected_source_runtime_digest=source_runtime,
        expected_backup_digest=backup, expected_rollback_digest=rollback,
        expected_manifest_digest=manifest,
        expected_previous_event_receipt_digest=_h("actual-prior"),
    )
    require(broken_result["ok"] is False)
    require("broken_event_lineage" in broken_result["errors"])
    blocked["broken-lineage"] = broken_result["errors"]

    summary = public_runtime_lifecycle_reliability_summary(samples)
    require(summary["event_count"] == len(EVENT_CLASSES))
    require(summary["event_class_count"] == len(EVENT_CLASSES))
    require(summary["operation_count"] == len(OPERATIONS))
    require(summary["all_events_valid"] is True)
    require(summary["exact_lineage_verified"] is True)
    require(summary["runtime_mutated"] is False)
    require(summary["authority_granted"] is False)

    privacy = package_privacy_summary_for_root(source)
    require(privacy.get("ok") is True)
    registry = inspect_checkpoint_registry(source_root=source)
    descriptor = next((row for row in registry["checkpoints"] if row["checkpoint_id"] == _CHECKPOINT_ID), None)
    require(descriptor is not None)
    require((descriptor or {}).get("contract_version") == CONTRACT_VERSION)
    require((descriptor or {}).get("builder") == "build_runtime_lifecycle_reliability_adversarial_checkpoint")
    require((descriptor or {}).get("read_only") is True)
    require((descriptor or {}).get("post_available") is False)
    require((descriptor or {}).get("required_input_count") == 0)
    require(not registry["duplicate_checkpoint_ids"])
    require(not registry["duplicate_builder_targets"])

    return {
        "ok": all(checks),
        "checkpoint_id": "runtime-lifecycle-reliability-adversarial:v1197.8",
        "contract_version": CONTRACT_VERSION,
        "passed": sum(checks),
        "total": len(checks),
        "summary": summary,
        "samples": samples,
        "blocked_cases": blocked,
        "privacy": privacy,
        "limitations": [
            "Evidence-only; no runtime data is read or changed.",
            "No backup, migration, upgrade, rollback, installation, recovery, or retry occurs.",
            "No approval or authority is created or consumed.",
            "The consolidated v1197.9 checkpoint remains deferred.",
        ],
    }
