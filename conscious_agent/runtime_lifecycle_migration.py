from __future__ import annotations

"""Content-free v1197.2 runtime lifecycle foundations.

The contract validates caller-supplied migration, backup, upgrade, rollback, and
fresh-install evidence. It never reads or writes runtime records, copies files,
changes schemas, installs software, or performs rollback. Lifecycle operations
remain proposals and evidence until a later operator-governed bundle.
"""

import hashlib
import json
import re
from typing import Any, Mapping, Sequence

CONTRACT_VERSION = "v1197.2"
LIFECYCLE_OPERATIONS = ("backup", "migration", "upgrade", "rollback", "fresh_install")
LIFECYCLE_STATES = (
    "proposed",
    "review_required",
    "evidence_only",
    "validated_evidence_only",
    "blocked",
    "failed_evidence_only",
    "inconclusive",
)
OUTCOMES = ("ready_for_operator_review", "blocked", "failed_evidence_only", "inconclusive")
PRIVATE_TOKENS = (
    "prompt", "conversation_text", "message", "memory_content", "memory_text",
    "secret", "password", "token_value", "raw_source", "source_text", "patch",
    "stdout", "stderr", "provider_payload", "private_reasoning", "api_key",
)
MAX_RECORDS = 16
MAX_EVIDENCE_BYTES = 100_000_000
MAX_RUNTIME_BYTES = 100_000_000_000
_VERSION_RE = re.compile(r"^[0-9]+(?:\.[0-9]+){1,3}$")


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


def create_lifecycle_plan(
    *,
    lifecycle_id: str,
    snapshot_digest: str,
    context_digest: str,
    source_version: str,
    target_version: str,
    source_schema_version: str,
    target_schema_version: str,
    source_runtime_digest: str,
    expected_backup_digest: str,
    expected_rollback_digest: str,
    purpose_code: str,
    max_records: int = 8,
    max_evidence_bytes: int = 10_000_000,
    max_runtime_bytes: int = 10_000_000_000,
) -> dict[str, Any]:
    plan: dict[str, Any] = {
        "contract_version": CONTRACT_VERSION,
        "lifecycle_id": str(lifecycle_id),
        "snapshot_digest": str(snapshot_digest),
        "context_digest": str(context_digest),
        "source_version": str(source_version),
        "target_version": str(target_version),
        "source_schema_version": str(source_schema_version),
        "target_schema_version": str(target_schema_version),
        "source_runtime_digest": str(source_runtime_digest),
        "expected_backup_digest": str(expected_backup_digest),
        "expected_rollback_digest": str(expected_rollback_digest),
        "purpose_code": str(purpose_code),
        "max_records": max_records,
        "max_evidence_bytes": max_evidence_bytes,
        "max_runtime_bytes": max_runtime_bytes,
        "content_free": True,
        "runtime_read": False,
        "backup_created": False,
        "migration_applied": False,
        "upgrade_applied": False,
        "rollback_applied": False,
        "fresh_install_performed": False,
        "files_written": False,
        "files_deleted": False,
        "runtime_mutated": False,
        "source_modified": False,
        "provider_contacted": False,
        "model_contacted": False,
        "thread_started": False,
        "process_started": False,
        "approval_created": False,
        "approval_consumed": False,
        "automatic_continuation": False,
        "authority_state": "separate_not_granted",
    }
    plan["plan_digest"] = _digest(plan)
    return plan


def create_lifecycle_evidence(
    *,
    lifecycle_id: str,
    evidence_id: str,
    operation: str,
    sequence: int,
    snapshot_digest: str,
    context_digest: str,
    source_version: str,
    target_version: str,
    source_schema_version: str,
    target_schema_version: str,
    input_runtime_digest: str,
    output_runtime_digest: str,
    backup_digest: str,
    rollback_digest: str,
    manifest_digest: str,
    artifact_digest: str,
    receipt_digest: str,
    previous_evidence_digest: str,
    estimated_runtime_bytes: int,
    estimated_evidence_bytes: int,
    purpose_code: str,
    lifecycle_state: str = "validated_evidence_only",
    outcome: str = "ready_for_operator_review",
) -> dict[str, Any]:
    row: dict[str, Any] = {
        "contract_version": CONTRACT_VERSION,
        "lifecycle_id": str(lifecycle_id),
        "evidence_id": str(evidence_id),
        "operation": str(operation),
        "sequence": sequence,
        "snapshot_digest": str(snapshot_digest),
        "context_digest": str(context_digest),
        "source_version": str(source_version),
        "target_version": str(target_version),
        "source_schema_version": str(source_schema_version),
        "target_schema_version": str(target_schema_version),
        "input_runtime_digest": str(input_runtime_digest),
        "output_runtime_digest": str(output_runtime_digest),
        "backup_digest": str(backup_digest),
        "rollback_digest": str(rollback_digest),
        "manifest_digest": str(manifest_digest),
        "artifact_digest": str(artifact_digest),
        "receipt_digest": str(receipt_digest),
        "previous_evidence_digest": str(previous_evidence_digest),
        "estimated_runtime_bytes": estimated_runtime_bytes,
        "estimated_evidence_bytes": estimated_evidence_bytes,
        "purpose_code": str(purpose_code),
        "lifecycle_state": str(lifecycle_state),
        "outcome": str(outcome),
        "backup_verified": operation in {"backup", "migration", "upgrade", "rollback"},
        "rollback_truth_preserved": True,
        "original_runtime_preserved": True,
        "fresh_install_isolated": operation == "fresh_install",
        "existing_runtime_untouched": True,
        "compatibility_verified": operation in {"migration", "upgrade", "rollback", "fresh_install"},
        "content_free": True,
        "runtime_read": False,
        "backup_created": False,
        "migration_applied": False,
        "upgrade_applied": False,
        "rollback_applied": False,
        "fresh_install_performed": False,
        "files_written": False,
        "files_deleted": False,
        "runtime_mutated": False,
        "source_modified": False,
        "provider_contacted": False,
        "model_contacted": False,
        "thread_started": False,
        "process_started": False,
        "approval_created": False,
        "approval_consumed": False,
        "automatic_continuation": False,
        "authority_state": "separate_not_granted",
    }
    row["evidence_digest"] = _digest(row)
    return row


def assess_runtime_lifecycle(
    plan: Mapping[str, Any],
    evidence: Sequence[Mapping[str, Any]],
    *,
    current_snapshot_digest: str,
    current_context_digest: str,
    verification_summary: Mapping[str, Any],
) -> dict[str, Any]:
    errors: list[str] = []
    plan_row = dict(plan)
    rows = [dict(row) for row in evidence]
    verification = dict(verification_summary)

    for field in _private_fields({"plan": plan_row, "evidence": rows, "verification": verification}):
        errors.append(f"private_field:{field}")

    supplied_plan_digest = plan_row.get("plan_digest")
    unsigned_plan = dict(plan_row)
    unsigned_plan.pop("plan_digest", None)
    if supplied_plan_digest != _digest(unsigned_plan): errors.append("plan_tamper")
    if plan_row.get("contract_version") != CONTRACT_VERSION: errors.append("unsupported_plan_contract")
    if not str(plan_row.get("lifecycle_id") or ""): errors.append("missing_lifecycle_id")
    for field in ("snapshot_digest", "context_digest", "source_runtime_digest", "expected_backup_digest", "expected_rollback_digest"):
        if not _is_digest(plan_row.get(field)): errors.append(f"malformed_plan_{field}")
    if plan_row.get("snapshot_digest") != current_snapshot_digest: errors.append("stale_plan_snapshot")
    if plan_row.get("context_digest") != current_context_digest: errors.append("stale_plan_context")
    for field in ("source_version", "target_version", "source_schema_version", "target_schema_version"):
        if not _VERSION_RE.fullmatch(str(plan_row.get(field) or "")): errors.append(f"malformed_{field}")
    if plan_row.get("source_version") == plan_row.get("target_version"): errors.append("version_transition_missing")
    for field, maximum in (("max_records", MAX_RECORDS), ("max_evidence_bytes", MAX_EVIDENCE_BYTES), ("max_runtime_bytes", MAX_RUNTIME_BYTES)):
        value = plan_row.get(field)
        if not isinstance(value, int) or isinstance(value, bool) or value < 1 or value > maximum:
            errors.append(f"malformed_{field}")

    expected_false = (
        "runtime_read", "backup_created", "migration_applied", "upgrade_applied", "rollback_applied",
        "fresh_install_performed", "files_written", "files_deleted", "runtime_mutated", "source_modified",
        "provider_contacted", "model_contacted", "thread_started", "process_started", "approval_created",
        "approval_consumed", "automatic_continuation",
    )
    for field in expected_false:
        if plan_row.get(field) is not False: errors.append(f"plan_forbidden_claim:{field}")
    if plan_row.get("content_free") is not True: errors.append("plan_not_content_free")
    if plan_row.get("authority_state") != "separate_not_granted": errors.append("plan_authority_expansion")

    if not isinstance(rows, list) or len(rows) != len(LIFECYCLE_OPERATIONS): errors.append("operation_coverage_mismatch")
    if len(rows) > int(plan_row.get("max_records") or 0): errors.append("oversized_evidence")
    ids = [str(row.get("evidence_id") or "") for row in rows]
    sequences = [row.get("sequence") for row in rows]
    if len(set(ids)) != len(ids) or any(not item for item in ids): errors.append("duplicate_or_missing_evidence_id")
    if sequences != list(range(1, len(rows) + 1)): errors.append("invalid_sequence")
    if [row.get("operation") for row in rows] != list(LIFECYCLE_OPERATIONS): errors.append("operation_order_mismatch")

    expected_previous = ""
    total_evidence_bytes = 0
    backup_digest = str(plan_row.get("expected_backup_digest") or "")
    rollback_digest = str(plan_row.get("expected_rollback_digest") or "")
    for index, row in enumerate(rows):
        supplied = row.get("evidence_digest")
        unsigned = dict(row); unsigned.pop("evidence_digest", None)
        if supplied != _digest(unsigned): errors.append(f"evidence_tamper:{index}")
        if row.get("contract_version") != CONTRACT_VERSION: errors.append(f"unsupported_evidence_contract:{index}")
        if row.get("lifecycle_id") != plan_row.get("lifecycle_id"): errors.append(f"lifecycle_mismatch:{index}")
        if row.get("snapshot_digest") != current_snapshot_digest: errors.append(f"stale_snapshot:{index}")
        if row.get("context_digest") != current_context_digest: errors.append(f"stale_context:{index}")
        if row.get("previous_evidence_digest") != expected_previous: errors.append(f"broken_lineage:{index}")
        if _is_digest(supplied): expected_previous = str(supplied)
        for field in (
            "snapshot_digest", "context_digest", "input_runtime_digest", "output_runtime_digest", "backup_digest",
            "rollback_digest", "manifest_digest", "artifact_digest", "receipt_digest", "evidence_digest",
        ):
            if not _is_digest(row.get(field)): errors.append(f"malformed_{field}:{index}")
        for field in ("source_version", "target_version", "source_schema_version", "target_schema_version"):
            if row.get(field) != plan_row.get(field): errors.append(f"version_or_schema_mismatch:{field}:{index}")
        if row.get("backup_digest") != backup_digest: errors.append(f"backup_truth_mismatch:{index}")
        if row.get("rollback_digest") != rollback_digest: errors.append(f"rollback_truth_mismatch:{index}")
        if row.get("lifecycle_state") not in LIFECYCLE_STATES: errors.append(f"unsupported_lifecycle_state:{index}")
        if row.get("outcome") not in OUTCOMES: errors.append(f"unsupported_outcome:{index}")
        for field in ("estimated_runtime_bytes", "estimated_evidence_bytes"):
            value = row.get(field)
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                errors.append(f"malformed_{field}:{index}")
        runtime_bytes = row.get("estimated_runtime_bytes")
        evidence_bytes = row.get("estimated_evidence_bytes")
        if isinstance(runtime_bytes, int) and runtime_bytes > int(plan_row.get("max_runtime_bytes") or 0): errors.append(f"runtime_budget_exceeded:{index}")
        if isinstance(evidence_bytes, int): total_evidence_bytes += max(0, evidence_bytes)
        if row.get("rollback_truth_preserved") is not True: errors.append(f"rollback_truth_lost:{index}")
        if row.get("original_runtime_preserved") is not True: errors.append(f"original_runtime_lost:{index}")
        if row.get("existing_runtime_untouched") is not True: errors.append(f"existing_runtime_touched:{index}")
        if row.get("operation") == "fresh_install" and row.get("fresh_install_isolated") is not True: errors.append("fresh_install_not_isolated")
        if row.get("operation") != "fresh_install" and row.get("fresh_install_isolated") is not False: errors.append(f"fresh_install_truth_mismatch:{index}")
        for field in expected_false:
            if row.get(field) is not False: errors.append(f"forbidden_claim:{field}:{index}")
        if row.get("content_free") is not True: errors.append(f"not_content_free:{index}")
        if row.get("authority_state") != "separate_not_granted": errors.append(f"authority_expansion:{index}")
    if total_evidence_bytes > int(plan_row.get("max_evidence_bytes") or 0): errors.append("evidence_budget_exceeded")

    if verification.get("content_free") is not True: errors.append("verification_not_content_free")
    if verification.get("current_regressions_separate") is not True: errors.append("current_regression_truth_missing")
    if verification.get("inherited_debt_visible") is not True: errors.append("inherited_debt_hidden")
    if verification.get("global_profile_pass_claimed") is not False: errors.append("false_global_profile_claim")

    status = "ready_for_operator_review" if not errors else "blocked"
    assessment: dict[str, Any] = {
        "contract_version": CONTRACT_VERSION,
        "status": status,
        "errors": sorted(set(errors)),
        "plan": plan_row,
        "evidence": rows,
        "operation_count": len(rows),
        "total_evidence_bytes": total_evidence_bytes,
        "exact_lineage_verified": not any("lineage" in error or "sequence" in error for error in errors),
        "backup_truth_preserved": not any("backup_truth" in error for error in errors),
        "rollback_truth_preserved": not any("rollback_truth" in error for error in errors),
        "original_runtime_preserved": not any("runtime_lost" in error or "runtime_touched" in error for error in errors),
        "content_free": True,
        "runtime_read": False,
        "backup_created": False,
        "migration_applied": False,
        "upgrade_applied": False,
        "rollback_applied": False,
        "fresh_install_performed": False,
        "files_written": False,
        "files_deleted": False,
        "runtime_mutated": False,
        "source_modified": False,
        "provider_contacted": False,
        "model_contacted": False,
        "thread_started": False,
        "process_started": False,
        "approval_created": False,
        "approval_consumed": False,
        "automatic_continuation": False,
        "global_profile_pass_claimed": False,
        "authority_state": "separate_not_granted",
    }
    assessment["assessment_digest"] = _digest({key: value for key, value in assessment.items() if key != "assessment_digest"})
    return assessment


def public_runtime_lifecycle_summary(assessment: Mapping[str, Any]) -> dict[str, Any]:
    plan = dict(assessment.get("plan") or {})
    rows = list(assessment.get("evidence") or [])
    return {
        "contract_version": CONTRACT_VERSION,
        "status": str(assessment.get("status") or "blocked"),
        "lifecycle_id": str(plan.get("lifecycle_id") or ""),
        "source_version": str(plan.get("source_version") or ""),
        "target_version": str(plan.get("target_version") or ""),
        "source_schema_version": str(plan.get("source_schema_version") or ""),
        "target_schema_version": str(plan.get("target_schema_version") or ""),
        "operation_count": len(rows),
        "operations": [str(row.get("operation") or "") for row in rows],
        "exact_lineage_verified": bool(assessment.get("exact_lineage_verified")),
        "backup_truth_preserved": bool(assessment.get("backup_truth_preserved")),
        "rollback_truth_preserved": bool(assessment.get("rollback_truth_preserved")),
        "original_runtime_preserved": bool(assessment.get("original_runtime_preserved")),
        "fresh_install_isolated": any(row.get("operation") == "fresh_install" and row.get("fresh_install_isolated") is True for row in rows),
        "error_count": len(assessment.get("errors") or []),
        "content_free": True,
        "runtime_read": False,
        "backup_created": False,
        "migration_applied": False,
        "upgrade_applied": False,
        "rollback_applied": False,
        "fresh_install_performed": False,
        "files_written": False,
        "files_deleted": False,
        "runtime_mutated": False,
        "source_modified": False,
        "provider_contacted": False,
        "model_contacted": False,
        "thread_started": False,
        "process_started": False,
        "approval_created": False,
        "approval_consumed": False,
        "automatic_continuation": False,
        "global_profile_pass_claimed": False,
        "authority_state": "separate_not_granted",
        "assessment_digest": str(assessment.get("assessment_digest") or ""),
    }
