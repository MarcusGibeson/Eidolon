from __future__ import annotations

"""Content-free v1197.8 runtime lifecycle reliability evidence.

The contract validates caller-supplied evidence about lifecycle failures and
adversarial conditions. It never reads runtime data, creates a backup, applies a
migration or upgrade, performs rollback, installs software, or starts recovery.
"""

import hashlib
import json
from typing import Any, Mapping

CONTRACT_VERSION = "v1197.8"
EVENT_CLASSES = (
    "stale_runtime_state",
    "backup_integrity_failure",
    "migration_interruption",
    "upgrade_interruption",
    "rollback_failure",
    "fresh_install_contamination",
    "schema_compatibility_drift",
    "recovery_reentry",
)
OPERATIONS = ("backup", "migration", "upgrade", "rollback", "fresh_install")
PRIVATE_TOKENS = (
    "prompt", "conversation_text", "message", "memory_content", "memory_text",
    "secret", "password", "token_value", "raw_source", "source_text", "patch",
    "stdout", "stderr", "provider_payload", "private_reasoning", "api_key",
)
MAX_SEQUENCE = 10_000
MAX_INTERRUPTION_COUNT = 128
MAX_FAILURE_COUNT = 128
MAX_DRIFT_SCORE = 100
MAX_LATENCY_MS = 60_000
MAX_LATENCY_BUDGET_MS = 10_000


def _digest(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str).encode("utf-8")
    ).hexdigest()


def _is_digest(value: object) -> bool:
    token = str(value or "")
    return len(token) == 64 and all(ch in "0123456789abcdef" for ch in token)


def _private_fields(value: object, prefix: str = "") -> list[str]:
    findings: list[str] = []
    if isinstance(value, Mapping):
        for key, item in value.items():
            label = f"{prefix}.{key}" if prefix else str(key)
            if any(token in str(key).lower() for token in PRIVATE_TOKENS):
                findings.append(label)
            findings.extend(_private_fields(item, label))
    elif isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            findings.extend(_private_fields(item, f"{prefix}[{index}]"))
    return sorted(set(findings))


def build_runtime_lifecycle_reliability_event(
    *,
    event_id: str,
    lifecycle_id: str,
    event_class: str,
    operation: str,
    sequence: int,
    snapshot_digest: str,
    context_digest: str,
    plan_digest: str,
    evidence_digest: str,
    assessment_digest: str,
    application_review_receipt_digest: str,
    source_runtime_digest: str,
    backup_digest: str,
    rollback_digest: str,
    manifest_digest: str,
    artifact_digest: str,
    receipt_digest: str,
    previous_event_receipt_digest: str = "",
    interruption_count: int = 0,
    integrity_failure_count: int = 0,
    rollback_failure_count: int = 0,
    contamination_finding_count: int = 0,
    schema_drift_score: int = 0,
    recovery_reentry_count: int = 0,
    foreground_latency_ms: int = 0,
    latency_budget_ms: int = 250,
) -> dict[str, Any]:
    row: dict[str, Any] = {
        "contract_version": CONTRACT_VERSION,
        "event_id": str(event_id),
        "lifecycle_id": str(lifecycle_id),
        "event_class": str(event_class),
        "operation": str(operation),
        "sequence": sequence,
        "snapshot_digest": str(snapshot_digest),
        "context_digest": str(context_digest),
        "plan_digest": str(plan_digest),
        "evidence_digest": str(evidence_digest),
        "assessment_digest": str(assessment_digest),
        "application_review_receipt_digest": str(application_review_receipt_digest),
        "source_runtime_digest": str(source_runtime_digest),
        "backup_digest": str(backup_digest),
        "rollback_digest": str(rollback_digest),
        "manifest_digest": str(manifest_digest),
        "artifact_digest": str(artifact_digest),
        "receipt_digest": str(receipt_digest),
        "previous_event_receipt_digest": str(previous_event_receipt_digest),
        "interruption_count": interruption_count,
        "integrity_failure_count": integrity_failure_count,
        "rollback_failure_count": rollback_failure_count,
        "contamination_finding_count": contamination_finding_count,
        "schema_drift_score": schema_drift_score,
        "recovery_reentry_count": recovery_reentry_count,
        "foreground_latency_ms": foreground_latency_ms,
        "latency_budget_ms": latency_budget_ms,
        "content_free": True,
        "original_runtime_preserved": True,
        "backup_truth_preserved": True,
        "rollback_truth_preserved": True,
        "existing_runtime_untouched": True,
        "foreground_available": True,
        "recovery_review_required": True,
        "runtime_read": False,
        "backup_created": False,
        "migration_applied": False,
        "upgrade_applied": False,
        "rollback_applied": False,
        "fresh_install_performed": False,
        "files_written": False,
        "files_deleted": False,
        "automatic_recovery": False,
        "automatic_retry": False,
        "provider_contacted": False,
        "model_contacted": False,
        "thread_started": False,
        "process_started": False,
        "approval_created": False,
        "approval_consumed": False,
        "runtime_mutated": False,
        "source_modified": False,
        "global_profile_pass_claimed": False,
        "authority_state": "separate_not_granted",
        "authority_granted": False,
    }
    row["event_digest"] = _digest(row)
    return row


def inspect_runtime_lifecycle_reliability_event(
    *,
    event: Mapping[str, Any],
    expected_lifecycle_id: str,
    expected_operation: str,
    expected_sequence: int,
    expected_snapshot_digest: str,
    expected_context_digest: str,
    expected_plan_digest: str,
    expected_evidence_digest: str,
    expected_assessment_digest: str,
    expected_application_review_receipt_digest: str,
    expected_source_runtime_digest: str,
    expected_backup_digest: str,
    expected_rollback_digest: str,
    expected_manifest_digest: str,
    expected_previous_event_receipt_digest: str = "",
) -> dict[str, Any]:
    row = dict(event)
    errors: list[str] = []

    for field in _private_fields(row):
        errors.append(f"private_field:{field}")

    body = dict(row)
    supplied_digest = body.pop("event_digest", None)
    if supplied_digest != _digest(body):
        errors.append("event_tamper")
    if row.get("contract_version") != CONTRACT_VERSION:
        errors.append("unsupported_contract")
    if not str(row.get("event_id") or ""):
        errors.append("missing_event_id")
    if row.get("lifecycle_id") != expected_lifecycle_id:
        errors.append("stale_lifecycle")
    if row.get("operation") != expected_operation:
        errors.append("operation_mismatch")
    if row.get("operation") not in OPERATIONS:
        errors.append("unsupported_operation")
    if row.get("event_class") not in EVENT_CLASSES:
        errors.append("unsupported_event_class")
    if row.get("sequence") != expected_sequence:
        errors.append("sequence_mismatch")
    sequence = row.get("sequence")
    if not isinstance(sequence, int) or isinstance(sequence, bool) or not 1 <= sequence <= MAX_SEQUENCE:
        errors.append("invalid_sequence")

    expected_digests = {
        "snapshot_digest": expected_snapshot_digest,
        "context_digest": expected_context_digest,
        "plan_digest": expected_plan_digest,
        "evidence_digest": expected_evidence_digest,
        "assessment_digest": expected_assessment_digest,
        "application_review_receipt_digest": expected_application_review_receipt_digest,
        "source_runtime_digest": expected_source_runtime_digest,
        "backup_digest": expected_backup_digest,
        "rollback_digest": expected_rollback_digest,
        "manifest_digest": expected_manifest_digest,
    }
    for field, expected in expected_digests.items():
        if not _is_digest(row.get(field)):
            errors.append(f"malformed_{field}")
        if row.get(field) != expected:
            errors.append(f"stale_{field}")
    for field in ("artifact_digest", "receipt_digest"):
        if not _is_digest(row.get(field)):
            errors.append(f"malformed_{field}")

    previous = row.get("previous_event_receipt_digest")
    if expected_sequence == 1:
        if previous not in ("", None):
            errors.append("unexpected_previous_event")
    elif previous != expected_previous_event_receipt_digest:
        errors.append("broken_event_lineage")

    bounds = {
        "interruption_count": (0, MAX_INTERRUPTION_COUNT),
        "integrity_failure_count": (0, MAX_FAILURE_COUNT),
        "rollback_failure_count": (0, MAX_FAILURE_COUNT),
        "contamination_finding_count": (0, MAX_FAILURE_COUNT),
        "schema_drift_score": (0, MAX_DRIFT_SCORE),
        "recovery_reentry_count": (0, MAX_FAILURE_COUNT),
        "foreground_latency_ms": (0, MAX_LATENCY_MS),
        "latency_budget_ms": (1, MAX_LATENCY_BUDGET_MS),
    }
    for field, (minimum, maximum) in bounds.items():
        value = row.get(field)
        if not isinstance(value, int) or isinstance(value, bool) or not minimum <= value <= maximum:
            errors.append(f"malformed_{field}")
    latency = row.get("foreground_latency_ms")
    budget = row.get("latency_budget_ms")
    if isinstance(latency, int) and isinstance(budget, int) and latency > budget:
        errors.append("foreground_latency_budget_exceeded")

    event_class = row.get("event_class")
    if event_class == "stale_runtime_state" and row.get("integrity_failure_count", 0) < 1:
        errors.append("stale_runtime_not_observed")
    if event_class == "backup_integrity_failure" and row.get("integrity_failure_count", 0) < 1:
        errors.append("backup_integrity_failure_not_observed")
    if event_class in {"migration_interruption", "upgrade_interruption"} and row.get("interruption_count", 0) < 1:
        errors.append("interruption_not_observed")
    if event_class == "rollback_failure" and row.get("rollback_failure_count", 0) < 1:
        errors.append("rollback_failure_not_observed")
    if event_class == "fresh_install_contamination" and row.get("contamination_finding_count", 0) < 1:
        errors.append("contamination_not_observed")
    if event_class == "schema_compatibility_drift" and row.get("schema_drift_score", 0) < 1:
        errors.append("schema_drift_not_observed")
    if event_class == "recovery_reentry" and row.get("recovery_reentry_count", 0) < 2:
        errors.append("recovery_reentry_not_observed")

    for field in (
        "content_free", "original_runtime_preserved", "backup_truth_preserved",
        "rollback_truth_preserved", "existing_runtime_untouched", "foreground_available",
        "recovery_review_required",
    ):
        if row.get(field) is not True:
            errors.append(f"invalid_{field}")
    for field in (
        "runtime_read", "backup_created", "migration_applied", "upgrade_applied",
        "rollback_applied", "fresh_install_performed", "files_written", "files_deleted",
        "automatic_recovery", "automatic_retry", "provider_contacted", "model_contacted",
        "thread_started", "process_started", "approval_created", "approval_consumed",
        "runtime_mutated", "source_modified", "global_profile_pass_claimed", "authority_granted",
    ):
        if row.get(field) is not False:
            errors.append(f"forbidden_claim:{field}")
    if row.get("authority_state") != "separate_not_granted":
        errors.append("authority_expansion")

    unique_errors = sorted(set(errors))
    result: dict[str, Any] = {
        "ok": not unique_errors,
        "contract_version": CONTRACT_VERSION,
        "status": "reliability_evidence_ready" if not unique_errors else "blocked",
        "errors": unique_errors,
        "event_class": row.get("event_class"),
        "operation": row.get("operation"),
        "sequence": row.get("sequence"),
        "content_free": True,
        "exact_lineage_verified": not unique_errors,
        "original_runtime_preserved": True,
        "backup_truth_preserved": True,
        "rollback_truth_preserved": True,
        "existing_runtime_untouched": True,
        "foreground_available": True,
        "recovery_review_required": True,
        "runtime_read": False,
        "backup_created": False,
        "migration_applied": False,
        "upgrade_applied": False,
        "rollback_applied": False,
        "fresh_install_performed": False,
        "files_written": False,
        "files_deleted": False,
        "automatic_recovery": False,
        "automatic_retry": False,
        "provider_contacted": False,
        "model_contacted": False,
        "thread_started": False,
        "process_started": False,
        "approval_created": False,
        "approval_consumed": False,
        "runtime_mutated": False,
        "source_modified": False,
        "global_profile_pass_claimed": False,
        "authority_state": "separate_not_granted",
        "authority_granted": False,
    }
    result["reliability_receipt_digest"] = _digest(result)
    return result


def public_runtime_lifecycle_reliability_summary(results: list[Mapping[str, Any]]) -> dict[str, Any]:
    rows = [dict(result) for result in results]
    summary: dict[str, Any] = {
        "contract_version": CONTRACT_VERSION,
        "event_count": len(rows),
        "event_class_count": len({row.get("event_class") for row in rows}),
        "operation_count": len({row.get("operation") for row in rows}),
        "all_events_valid": bool(rows) and all(row.get("ok") is True for row in rows),
        "content_free": True,
        "exact_lineage_verified": bool(rows) and all(row.get("exact_lineage_verified") is True for row in rows),
        "original_runtime_preserved": True,
        "backup_truth_preserved": True,
        "rollback_truth_preserved": True,
        "existing_runtime_untouched": True,
        "foreground_available": True,
        "recovery_review_required": True,
        "runtime_read": False,
        "backup_created": False,
        "migration_applied": False,
        "upgrade_applied": False,
        "rollback_applied": False,
        "fresh_install_performed": False,
        "automatic_recovery": False,
        "automatic_retry": False,
        "runtime_mutated": False,
        "authority_state": "separate_not_granted",
        "authority_granted": False,
        "global_profile_pass_claimed": False,
    }
    summary["summary_digest"] = _digest(summary)
    return summary
