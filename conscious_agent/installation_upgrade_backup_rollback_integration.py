from __future__ import annotations

"""v1242 supervised installation, upgrade, backup, restore, and rollback integration.

This module prepares and reviews content-free lifecycle evidence.  It binds exact
installation state, package, manifest, compatibility, backup, migration,
verification, and rollback digests.  It never invokes the historical installer,
stages files, copies backups, changes an installation, resumes a transaction, or
grants mutation authority.  Those operations remain behind their own exact,
single-use authorization paths.
"""

import os
import re
import shutil
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterable, Mapping

from ordinary_chat_development_campaign import _atomic_json, _digest, _read_json, _store_root

SCHEMA_VERSION = "1"
CONTRACT_VERSION = "v1242.8"
MILESTONE_NAME = "Installation, Upgrade, Backup, and Rollback Integration"
ROADMAP_PATH = "Balanced Mind-and-Action Path 3"
MAX_RECORDS = 300

OPERATIONS = {"install", "upgrade", "restore", "rollback"}
INSTALLATION_STATES = {"absent", "healthy", "degraded", "partial", "unknown"}
COMPATIBILITY_STATES = {"compatible", "incompatible", "unknown", "migration_required"}
BACKUP_REQUIREMENTS = {"required", "optional", "not_applicable"}
PROPOSAL_DISPOSITIONS = {"accept_proposal", "hold", "reject", "request_changes"}
RECOVERY_DISPOSITIONS = {"acknowledge", "hold", "reject_evidence", "request_changes"}
RECOVERY_STATES = {"not_started", "backup_complete", "migration_partial", "apply_partial", "verification_failed", "interrupted", "complete", "unknown"}
RECOVERY_ACTIONS = {"no_action", "prepare_resume_proposal", "prepare_rollback_proposal", "manual_reconciliation_required", "hold_for_evidence"}

AUTHORITY_FLAGS = {
    "lifecycle_preflight_preparation_authorized": True,
    "lifecycle_proposal_preparation_authorized": True,
    "lifecycle_review_authorized": True,
    "recovery_assessment_preparation_authorized": True,
    "recovery_review_authorized": True,
    "installation_authorized": False,
    "upgrade_authorized": False,
    "backup_execution_authorized": False,
    "restore_authorized": False,
    "rollback_authorized": False,
    "launch_authorized": False,
    "pause_authorized": False,
    "resume_authorized": False,
    "cancel_authorized": False,
    "migration_execution_authorized": False,
    "verification_execution_authorized": False,
    "provider_execution_authorized": False,
    "command_execution_authorized": False,
    "test_execution_authorized": False,
    "dependency_installation_authorized": False,
    "runtime_download_authorized": False,
    "project_mutation_authorized": False,
    "queue_mutation_authorized": False,
    "schedule_mutation_authorized": False,
    "cognition_write_authorized": False,
    "approval_creation_authorized": False,
    "approval_consumption_authorized": False,
    "automatic_continuation_authorized": False,
    "automatic_retry_authorized": False,
    "background_execution_authorized": False,
    "promotion_authorized": False,
    "certification_authorized": False,
    "release_authorized": False,
    "model_management_authorized": False,
    "old_authority_reusable": False,
}

_TOKEN = re.compile(r"^[a-z][a-z0-9_-]{1,95}$")
_HEX64 = re.compile(r"^[a-f0-9]{64}$")
_VERSION = re.compile(r"^(?:none|[0-9]+(?:\.[0-9]+){1,3})$")
_PRIVATE = ("path", "secret", "password", "token", "credential", "content", "prompt", "stdout", "stderr", "provider", "source_text", "private")

_REVIEW_PROPOSAL = re.compile(
    r"^review lifecycle proposal (?P<decision>accept_proposal|hold|reject|request_changes) "
    r"for proposal (?P<proposal>lifecycle_proposal_[a-f0-9]{24}) digest (?P<digest>[a-f0-9]{64})[.!?]*$",
    re.I,
)
_REVIEW_RECOVERY = re.compile(
    r"^review lifecycle recovery (?P<decision>acknowledge|hold|reject_evidence|request_changes) "
    r"for assessment (?P<assessment>lifecycle_recovery_[a-f0-9]{24}) digest (?P<digest>[a-f0-9]{64})[.!?]*$",
    re.I,
)
_SHOW_REGISTRY = re.compile(r"^show installation lifecycle registry[.!?]*$", re.I)
_SHOW_PREFLIGHTS = re.compile(r"^show installation lifecycle preflights[.!?]*$", re.I)
_SHOW_PROPOSALS = re.compile(r"^show installation lifecycle proposals[.!?]*$", re.I)
_SHOW_REVIEWS = re.compile(r"^show installation lifecycle reviews[.!?]*$", re.I)
_SHOW_RECOVERY = re.compile(r"^show installation lifecycle recovery assessments[.!?]*$", re.I)
_SHOW_RECOVERY_REVIEWS = re.compile(r"^show installation lifecycle recovery reviews[.!?]*$", re.I)


def _root(runtime_root=None) -> Path:
    return _store_root(runtime_root)


def _dir(name: str, runtime_root=None) -> Path:
    return _root(runtime_root) / name


def _path(name: str, record_id: str, runtime_root=None) -> Path:
    return _dir(name, runtime_root) / f"{str(record_id or '').lower()}.json"


@contextmanager
def _lock(runtime_root=None):
    path = _root(runtime_root) / "locks" / "installation-lifecycle-integration.lock"
    path.parent.mkdir(parents=True, exist_ok=True)
    deadline = time.monotonic() + 15.0
    while True:
        try:
            path.mkdir()
            (path / "owner").write_text(str(os.getpid()), encoding="ascii")
            break
        except FileExistsError:
            try:
                if time.time() - path.stat().st_mtime > 60:
                    shutil.rmtree(path, ignore_errors=True)
                    continue
            except FileNotFoundError:
                continue
            if time.monotonic() >= deadline:
                raise TimeoutError("Timed out waiting for installation lifecycle lock")
            time.sleep(0.02)
    try:
        yield
    finally:
        shutil.rmtree(path, ignore_errors=True)


def _sealed(record: Mapping[str, Any], field: str) -> dict[str, Any]:
    row = dict(record)
    row[field] = _digest({key: value for key, value in row.items() if key != field})
    return row


def _valid(record: Mapping[str, Any], field: str) -> bool:
    supplied = str(record.get(field) or "")
    return bool(supplied and supplied == _digest({key: value for key, value in record.items() if key != field}))


def _hex(value: Any, reason: str, *, allow_empty: bool = False) -> str:
    text = str(value or "").lower().strip()
    if allow_empty and not text:
        return ""
    if not _HEX64.fullmatch(text):
        raise ValueError(reason)
    return text


def _token(value: Any, reason: str) -> str:
    text = str(value or "").lower().strip()
    if not _TOKEN.fullmatch(text) or any(part in text for part in ("..", "/", "\\")) or any(part in text for part in _PRIVATE):
        raise ValueError(reason)
    return text


def _version(value: Any, reason: str) -> str:
    text = str(value or "").lower().strip()
    if not _VERSION.fullmatch(text):
        raise ValueError(reason)
    return text


def _base() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "contract_version": CONTRACT_VERSION,
        "content_free": True,
        "runtime_records_external": True,
        "installation_scoped": True,
        "operator_review_required": True,
        "historical_records_immutable": True,
        "exact_target_and_artifact_lineage_required": True,
        "exact_backup_and_rollback_lineage_required": True,
        "fresh_separate_mutation_authority_required": True,
        "paths_suppressed": True,
        "raw_manifest_content_exposed": False,
        "raw_backup_content_exposed": False,
        "raw_migration_content_exposed": False,
        "raw_verification_output_exposed": False,
        "runtime_state_read": False,
        "provider_contacted": False,
        "commands_executed": False,
        "tests_executed": False,
        "files_copied": False,
        "files_written": False,
        "files_deleted": False,
        "installation_modified": False,
        "backup_created": False,
        "restore_performed": False,
        "rollback_performed": False,
        "migration_performed": False,
        "verification_performed": False,
        "queue_modified": False,
        "schedule_modified": False,
        "cognition_written": False,
        "approval_created": False,
        "approval_consumed": False,
        "automatic_continuation_created": False,
        "hidden_retry_created": False,
        **AUTHORITY_FLAGS,
    }


def _failure(status: str, reason: str = "") -> dict[str, Any]:
    row = {"ok": False, "status": status, "reason": reason, **_base()}
    row["lifecycle_integration_result_digest"] = _digest(row)
    return row


def lifecycle_operation_registry() -> dict[str, Any]:
    rows = [
        {"operation": "install", "current_state": "absent", "backup_requirement": "not_applicable", "target_version_required": True},
        {"operation": "upgrade", "current_state": "healthy", "backup_requirement": "required", "target_version_required": True},
        {"operation": "restore", "current_state": "degraded_or_partial", "backup_requirement": "required", "target_version_required": True},
        {"operation": "rollback", "current_state": "healthy_degraded_or_partial", "backup_requirement": "required", "target_version_required": True},
    ]
    result = {
        "ok": True,
        "status": "installation_lifecycle_registry_ready",
        "operations": rows,
        "operation_count": len(rows),
        "proposal_dispositions": sorted(PROPOSAL_DISPOSITIONS),
        "recovery_dispositions": sorted(RECOVERY_DISPOSITIONS),
        "recovery_states": sorted(RECOVERY_STATES),
        "recovery_actions": sorted(RECOVERY_ACTIONS),
        "inspection_only": True,
        **_base(),
    }
    result["registry_digest"] = _digest(result)
    return result


def _preflight_state(operation: str, current_version: str, target_version: str, installation_state: str, compatibility_state: str, backup_requirement: str) -> tuple[str, list[str]]:
    issues: list[str] = []
    if operation == "install":
        if current_version != "none" or installation_state != "absent":
            issues.append("install_requires_absent_target")
        if backup_requirement != "not_applicable":
            issues.append("fresh_install_backup_requirement_must_be_not_applicable")
    else:
        if current_version == "none" or installation_state == "absent":
            issues.append("existing_installation_required")
        if backup_requirement != "required":
            issues.append("backup_required_for_mutating_existing_installation")
    if operation == "upgrade" and current_version == target_version:
        issues.append("upgrade_version_transition_required")
    if operation in {"restore", "rollback"} and target_version == "none":
        issues.append("restore_or_rollback_target_version_required")
    if compatibility_state == "incompatible":
        issues.append("target_incompatible")
    if compatibility_state == "unknown":
        issues.append("compatibility_evidence_missing")
    if installation_state == "unknown":
        issues.append("installation_state_unknown")
    if operation == "upgrade" and installation_state in {"partial", "degraded"}:
        issues.append("unhealthy_installation_requires_recovery_review")
    return ("ready_for_operator_review" if not issues else "blocked"), sorted(set(issues))


def prepare_installation_lifecycle_preflight(
    target_reference: str,
    *,
    operation: str,
    current_version: str,
    target_version: str,
    installation_state: str,
    compatibility_state: str,
    backup_requirement: str,
    current_installation_digest: str,
    current_inventory_digest: str,
    target_artifact_digest: str,
    target_manifest_digest: str,
    compatibility_evidence_digest: str,
    runtime_schema_digest: str,
    lifecycle_policy_digest: str,
    runtime_root=None,
) -> dict[str, Any]:
    try:
        target = _token(target_reference, "invalid_target_reference")
        op = str(operation or "").lower().strip()
        if op not in OPERATIONS:
            raise ValueError("unsupported_lifecycle_operation")
        current = _version(current_version, "invalid_current_version")
        target_version_value = _version(target_version, "invalid_target_version")
        state = str(installation_state or "").lower().strip()
        if state not in INSTALLATION_STATES:
            raise ValueError("invalid_installation_state")
        compatibility = str(compatibility_state or "").lower().strip()
        if compatibility not in COMPATIBILITY_STATES:
            raise ValueError("invalid_compatibility_state")
        backup = str(backup_requirement or "").lower().strip()
        if backup not in BACKUP_REQUIREMENTS:
            raise ValueError("invalid_backup_requirement")
        digests = {
            "current_installation_digest": _hex(current_installation_digest, "invalid_current_installation_digest", allow_empty=op == "install"),
            "current_inventory_digest": _hex(current_inventory_digest, "invalid_current_inventory_digest", allow_empty=op == "install"),
            "target_artifact_digest": _hex(target_artifact_digest, "invalid_target_artifact_digest"),
            "target_manifest_digest": _hex(target_manifest_digest, "invalid_target_manifest_digest"),
            "compatibility_evidence_digest": _hex(compatibility_evidence_digest, "invalid_compatibility_evidence_digest"),
            "runtime_schema_digest": _hex(runtime_schema_digest, "invalid_runtime_schema_digest"),
            "lifecycle_policy_digest": _hex(lifecycle_policy_digest, "invalid_lifecycle_policy_digest"),
        }
    except ValueError as exc:
        return _failure("installation_lifecycle_preflight_blocked", str(exc))

    state_result, issues = _preflight_state(op, current, target_version_value, state, compatibility, backup)
    basis = {
        "target_reference": target,
        "operation": op,
        "current_version": current,
        "target_version": target_version_value,
        "installation_state": state,
        "compatibility_state": compatibility,
        "backup_requirement": backup,
        **digests,
    }
    preflight_id = f"lifecycle_preflight_{_digest(basis)[:24]}"
    row = _sealed({
        "ok": state_result == "ready_for_operator_review",
        "status": f"installation_lifecycle_preflight_{state_result}",
        "preflight_id": preflight_id,
        **basis,
        "issue_codes": issues,
        "issue_count": len(issues),
        "preflight_acceptable": not issues,
        "backup_must_precede_mutation": backup == "required",
        "migration_preview_required": compatibility == "migration_required",
        "fresh_target_revalidation_required": True,
        "fresh_artifact_revalidation_required": True,
        "operator_review_phrase": "",
        **_base(),
    }, "preflight_record_digest")
    row["operator_review_phrase"] = f"Prepare installation lifecycle proposal for preflight {preflight_id} digest {row['preflight_record_digest']}."
    row = _sealed(row, "preflight_record_digest")
    with _lock(runtime_root):
        path = _path("installation_lifecycle_preflights", preflight_id, runtime_root)
        existing = _read_json(path)
        if existing:
            return {"ok": _valid(existing, "preflight_record_digest") and bool(existing.get("ok")), **existing, **_base()}
        _atomic_json(path, row)
    return row


def load_installation_lifecycle_preflight(preflight_id: str, *, runtime_root=None) -> dict[str, Any]:
    row = _read_json(_path("installation_lifecycle_preflights", preflight_id, runtime_root))
    if not row:
        return _failure("installation_lifecycle_preflight_missing", preflight_id)
    if not _valid(row, "preflight_record_digest"):
        return _failure("installation_lifecycle_preflight_tampered", preflight_id)
    return {"ok": bool(row.get("ok")), **row, **_base()}


def prepare_installation_lifecycle_proposal(
    preflight_id: str,
    *,
    expected_preflight_digest: str,
    current_target_digest: str,
    backup_evidence_digest: str,
    backup_manifest_digest: str,
    backup_restore_verification_digest: str,
    migration_preview_digest: str,
    verification_plan_digest: str,
    rollback_plan_digest: str,
    rollback_target_digest: str,
    disk_space_evidence_digest: str,
    backup_verified: bool,
    rollback_feasible: bool,
    migration_reversible: bool,
    estimated_change_count: int,
    runtime_root=None,
) -> dict[str, Any]:
    preflight = load_installation_lifecycle_preflight(preflight_id, runtime_root=runtime_root)
    if not preflight.get("preflight_id"):
        return preflight
    try:
        expected = _hex(expected_preflight_digest, "invalid_preflight_digest")
        if expected != str(preflight.get("preflight_record_digest") or ""):
            raise ValueError("stale_or_mismatched_preflight_digest")
        current_target = _hex(current_target_digest, "invalid_current_target_digest", allow_empty=preflight.get("operation") == "install")
        backup_evidence = _hex(backup_evidence_digest, "invalid_backup_evidence_digest", allow_empty=preflight.get("backup_requirement") == "not_applicable")
        backup_manifest = _hex(backup_manifest_digest, "invalid_backup_manifest_digest", allow_empty=preflight.get("backup_requirement") == "not_applicable")
        restore_verification = _hex(backup_restore_verification_digest, "invalid_backup_restore_verification_digest", allow_empty=preflight.get("backup_requirement") == "not_applicable")
        migration_preview = _hex(migration_preview_digest, "invalid_migration_preview_digest", allow_empty=not preflight.get("migration_preview_required"))
        verification = _hex(verification_plan_digest, "invalid_verification_plan_digest")
        rollback_plan = _hex(rollback_plan_digest, "invalid_rollback_plan_digest")
        rollback_target = _hex(rollback_target_digest, "invalid_rollback_target_digest", allow_empty=preflight.get("operation") == "install")
        disk_space = _hex(disk_space_evidence_digest, "invalid_disk_space_evidence_digest")
        count = int(estimated_change_count)
        if count < 0 or count > 1_000_000:
            raise ValueError("invalid_estimated_change_count")
    except (ValueError, TypeError) as exc:
        return _failure("installation_lifecycle_proposal_blocked", str(exc))

    issues = list(preflight.get("issue_codes") or [])
    if not preflight.get("preflight_acceptable"):
        issues.append("preflight_not_acceptable")
    expected_current = str(preflight.get("current_installation_digest") or "")
    if current_target != expected_current:
        issues.append("target_state_changed_after_preflight")
    if preflight.get("backup_requirement") == "required" and not backup_verified:
        issues.append("verified_backup_required")
    if preflight.get("backup_requirement") == "required" and not all((backup_evidence, backup_manifest, restore_verification)):
        issues.append("backup_evidence_incomplete")
    if not rollback_feasible:
        issues.append("rollback_not_feasible")
    if preflight.get("migration_preview_required") and not migration_preview:
        issues.append("migration_preview_required")
    if preflight.get("migration_preview_required") and not migration_reversible:
        issues.append("migration_not_reversible")
    issues = sorted(set(issues))

    stages = [
        {"stage": "preflight_revalidation", "required": True, "evidence_digest": str(preflight.get("preflight_record_digest") or "")},
        {"stage": "backup", "required": preflight.get("backup_requirement") == "required", "evidence_digest": backup_evidence},
        {"stage": "migration_preview", "required": bool(preflight.get("migration_preview_required")), "evidence_digest": migration_preview},
        {"stage": "staged_apply", "required": True, "evidence_digest": str(preflight.get("target_artifact_digest") or "")},
        {"stage": "verification", "required": True, "evidence_digest": verification},
        {"stage": "rollback", "required": True, "evidence_digest": rollback_plan},
    ]
    basis = {
        "preflight_id": preflight_id,
        "preflight_record_digest": expected,
        "target_reference": preflight.get("target_reference"),
        "operation": preflight.get("operation"),
        "current_version": preflight.get("current_version"),
        "target_version": preflight.get("target_version"),
        "current_target_digest": current_target,
        "backup_evidence_digest": backup_evidence,
        "backup_manifest_digest": backup_manifest,
        "backup_restore_verification_digest": restore_verification,
        "migration_preview_digest": migration_preview,
        "verification_plan_digest": verification,
        "rollback_plan_digest": rollback_plan,
        "rollback_target_digest": rollback_target,
        "disk_space_evidence_digest": disk_space,
        "estimated_change_count": count,
        "stages": stages,
    }
    proposal_id = f"lifecycle_proposal_{_digest(basis)[:24]}"
    row = _sealed({
        "ok": not issues,
        "status": "installation_lifecycle_proposal_ready_for_operator_review" if not issues else "installation_lifecycle_proposal_blocked",
        "proposal_id": proposal_id,
        **basis,
        "issue_codes": issues,
        "issue_count": len(issues),
        "backup_verified": bool(backup_verified),
        "rollback_feasible": bool(rollback_feasible),
        "migration_reversible": bool(migration_reversible),
        "proposal_acceptable": not issues,
        "staged_apply_only": True,
        "verification_required_before_completion": True,
        "rollback_bound_to_exact_backup_and_target": True,
        "operator_review_phrase": "",
        **_base(),
    }, "proposal_record_digest")
    row["operator_review_phrase"] = f"Review lifecycle proposal accept_proposal for proposal {proposal_id} digest {row['proposal_record_digest']}."
    row = _sealed(row, "proposal_record_digest")
    with _lock(runtime_root):
        path = _path("installation_lifecycle_proposals", proposal_id, runtime_root)
        existing = _read_json(path)
        if existing:
            return {"ok": _valid(existing, "proposal_record_digest") and bool(existing.get("ok")), **existing, **_base()}
        _atomic_json(path, row)
    return row


def load_installation_lifecycle_proposal(proposal_id: str, *, runtime_root=None) -> dict[str, Any]:
    row = _read_json(_path("installation_lifecycle_proposals", proposal_id, runtime_root))
    if not row:
        return _failure("installation_lifecycle_proposal_missing", proposal_id)
    if not _valid(row, "proposal_record_digest"):
        return _failure("installation_lifecycle_proposal_tampered", proposal_id)
    return {"ok": bool(row.get("ok")), **row, **_base()}


def review_installation_lifecycle_proposal(
    proposal_id: str,
    *,
    expected_proposal_digest: str,
    disposition: str,
    exact_phrase: str,
    runtime_root=None,
) -> dict[str, Any]:
    proposal = load_installation_lifecycle_proposal(proposal_id, runtime_root=runtime_root)
    if not proposal.get("proposal_id"):
        return proposal
    try:
        expected = _hex(expected_proposal_digest, "invalid_proposal_digest")
        decision = str(disposition or "").lower().strip()
        if decision not in PROPOSAL_DISPOSITIONS:
            raise ValueError("invalid_proposal_disposition")
        required = f"Review lifecycle proposal {decision} for proposal {proposal_id} digest {expected}."
        if str(exact_phrase or "") != required:
            raise ValueError("exact_review_phrase_required")
        if expected != str(proposal.get("proposal_record_digest") or ""):
            raise ValueError("stale_or_mismatched_proposal_digest")
        if decision == "accept_proposal" and not proposal.get("proposal_acceptable"):
            raise ValueError("blocked_proposal_cannot_be_accepted")
    except ValueError as exc:
        return _failure("installation_lifecycle_proposal_review_blocked", str(exc))

    basis = {"proposal_id": proposal_id, "proposal_record_digest": expected, "target_reference": proposal.get("target_reference"), "operation": proposal.get("operation"), "disposition": decision}
    review_id = f"lifecycle_review_{_digest(basis)[:24]}"
    row = _sealed({
        "ok": True,
        "status": "installation_lifecycle_proposal_review_recorded",
        "review_id": review_id,
        **basis,
        "proposal_interpretation_accepted": decision == "accept_proposal",
        "operator_follow_up_required": decision != "accept_proposal",
        "fresh_installation_authority_still_required": True,
        "backup_execution_authorized_by_review": False,
        "migration_execution_authorized_by_review": False,
        "installation_authorized_by_review": False,
        "upgrade_authorized_by_review": False,
        "restore_authorized_by_review": False,
        "rollback_authorized_by_review": False,
        **_base(),
    }, "review_record_digest")
    with _lock(runtime_root):
        path = _path("installation_lifecycle_reviews", review_id, runtime_root)
        existing = _read_json(path)
        if existing:
            return {"ok": _valid(existing, "review_record_digest"), **existing, **_base()}
        _atomic_json(path, row)
    return row


def load_installation_lifecycle_review(review_id: str, *, runtime_root=None) -> dict[str, Any]:
    row = _read_json(_path("installation_lifecycle_reviews", review_id, runtime_root))
    if not row:
        return _failure("installation_lifecycle_review_missing", review_id)
    if not _valid(row, "review_record_digest"):
        return _failure("installation_lifecycle_review_tampered", review_id)
    return {"ok": True, **row, **_base()}


def prepare_installation_lifecycle_recovery_assessment(
    proposal_id: str,
    *,
    expected_proposal_digest: str,
    proposal_review_id: str,
    expected_review_digest: str,
    observed_state: str,
    transaction_evidence_digest: str,
    observed_target_digest: str,
    observed_backup_digest: str,
    completed_stage_count: int,
    evidence_complete: bool,
    runtime_root=None,
) -> dict[str, Any]:
    proposal = load_installation_lifecycle_proposal(proposal_id, runtime_root=runtime_root)
    review = load_installation_lifecycle_review(proposal_review_id, runtime_root=runtime_root)
    if not proposal.get("proposal_id"):
        return proposal
    if not review.get("review_id"):
        return review
    try:
        expected_proposal = _hex(expected_proposal_digest, "invalid_proposal_digest")
        expected_review = _hex(expected_review_digest, "invalid_review_digest")
        state = str(observed_state or "").lower().strip()
        if state not in RECOVERY_STATES:
            raise ValueError("invalid_recovery_state")
        transaction = _hex(transaction_evidence_digest, "invalid_transaction_evidence_digest")
        target = _hex(observed_target_digest, "invalid_observed_target_digest", allow_empty=state == "not_started")
        backup = _hex(observed_backup_digest, "invalid_observed_backup_digest", allow_empty=proposal.get("backup_evidence_digest") == "")
        count = int(completed_stage_count)
        if count < 0 or count > len(proposal.get("stages") or []):
            raise ValueError("invalid_completed_stage_count")
        if expected_proposal != proposal.get("proposal_record_digest") or expected_review != review.get("review_record_digest"):
            raise ValueError("stale_or_mismatched_recovery_lineage")
        if review.get("proposal_id") != proposal_id or review.get("proposal_record_digest") != expected_proposal:
            raise ValueError("proposal_review_lineage_mismatch")
        if not review.get("proposal_interpretation_accepted"):
            raise ValueError("accepted_proposal_review_required")
    except (ValueError, TypeError) as exc:
        return _failure("installation_lifecycle_recovery_assessment_blocked", str(exc))

    issues: list[str] = []
    if not evidence_complete:
        issues.append("recovery_evidence_incomplete")
    expected_backup = str(proposal.get("backup_evidence_digest") or "")
    if expected_backup and backup != expected_backup:
        issues.append("backup_digest_mismatch")
    if state == "complete":
        action = "no_action" if not issues else "manual_reconciliation_required"
    elif not evidence_complete or state == "unknown":
        action = "hold_for_evidence"
    elif state in {"backup_complete", "migration_partial", "interrupted"} and not issues:
        action = "prepare_resume_proposal"
    elif state in {"apply_partial", "verification_failed"} and not issues:
        action = "prepare_rollback_proposal"
    elif state == "not_started":
        action = "hold_for_evidence"
    else:
        action = "manual_reconciliation_required"
    if issues and action not in {"hold_for_evidence", "manual_reconciliation_required"}:
        action = "manual_reconciliation_required"

    basis = {
        "proposal_id": proposal_id,
        "proposal_record_digest": expected_proposal,
        "proposal_review_id": proposal_review_id,
        "proposal_review_digest": expected_review,
        "target_reference": proposal.get("target_reference"),
        "operation": proposal.get("operation"),
        "observed_state": state,
        "transaction_evidence_digest": transaction,
        "observed_target_digest": target,
        "observed_backup_digest": backup,
        "completed_stage_count": count,
        "evidence_complete": bool(evidence_complete),
        "recommended_action": action,
    }
    assessment_id = f"lifecycle_recovery_{_digest(basis)[:24]}"
    row = _sealed({
        "ok": not issues,
        "status": "installation_lifecycle_recovery_ready_for_operator_review" if not issues else "installation_lifecycle_recovery_attention_required",
        "assessment_id": assessment_id,
        **basis,
        "issue_codes": sorted(set(issues)),
        "issue_count": len(set(issues)),
        "resume_proposal_only": action == "prepare_resume_proposal",
        "rollback_proposal_only": action == "prepare_rollback_proposal",
        "automatic_resume_permitted": False,
        "automatic_rollback_permitted": False,
        "operator_review_phrase": "",
        **_base(),
    }, "assessment_record_digest")
    row["operator_review_phrase"] = f"Review lifecycle recovery acknowledge for assessment {assessment_id} digest {row['assessment_record_digest']}."
    row = _sealed(row, "assessment_record_digest")
    with _lock(runtime_root):
        path = _path("installation_lifecycle_recovery_assessments", assessment_id, runtime_root)
        existing = _read_json(path)
        if existing:
            return {"ok": _valid(existing, "assessment_record_digest") and bool(existing.get("ok")), **existing, **_base()}
        _atomic_json(path, row)
    return row


def load_installation_lifecycle_recovery_assessment(assessment_id: str, *, runtime_root=None) -> dict[str, Any]:
    row = _read_json(_path("installation_lifecycle_recovery_assessments", assessment_id, runtime_root))
    if not row:
        return _failure("installation_lifecycle_recovery_assessment_missing", assessment_id)
    if not _valid(row, "assessment_record_digest"):
        return _failure("installation_lifecycle_recovery_assessment_tampered", assessment_id)
    return {"ok": bool(row.get("ok")), **row, **_base()}


def review_installation_lifecycle_recovery(
    assessment_id: str,
    *,
    expected_assessment_digest: str,
    disposition: str,
    exact_phrase: str,
    runtime_root=None,
) -> dict[str, Any]:
    assessment = load_installation_lifecycle_recovery_assessment(assessment_id, runtime_root=runtime_root)
    if not assessment.get("assessment_id"):
        return assessment
    try:
        expected = _hex(expected_assessment_digest, "invalid_assessment_digest")
        decision = str(disposition or "").lower().strip()
        if decision not in RECOVERY_DISPOSITIONS:
            raise ValueError("invalid_recovery_disposition")
        required = f"Review lifecycle recovery {decision} for assessment {assessment_id} digest {expected}."
        if str(exact_phrase or "") != required:
            raise ValueError("exact_review_phrase_required")
        if expected != assessment.get("assessment_record_digest"):
            raise ValueError("stale_or_mismatched_assessment_digest")
    except ValueError as exc:
        return _failure("installation_lifecycle_recovery_review_blocked", str(exc))
    basis = {"assessment_id": assessment_id, "assessment_record_digest": expected, "proposal_id": assessment.get("proposal_id"), "target_reference": assessment.get("target_reference"), "disposition": decision}
    review_id = f"lifecycle_recovery_review_{_digest(basis)[:24]}"
    row = _sealed({
        "ok": True,
        "status": "installation_lifecycle_recovery_review_recorded",
        "review_id": review_id,
        **basis,
        "recovery_interpretation_acknowledged": decision == "acknowledge",
        "recommended_action": assessment.get("recommended_action"),
        "resume_authority_created": False,
        "rollback_authority_created": False,
        "fresh_exact_recovery_authority_still_required": True,
        **_base(),
    }, "review_record_digest")
    with _lock(runtime_root):
        path = _path("installation_lifecycle_recovery_reviews", review_id, runtime_root)
        existing = _read_json(path)
        if existing:
            return {"ok": _valid(existing, "review_record_digest"), **existing, **_base()}
        _atomic_json(path, row)
    return row


def _project(row: Mapping[str, Any], keys: Iterable[str]) -> dict[str, Any]:
    return {key: row.get(key) for key in keys if key in row}


_PREFLIGHT_PUBLIC = ("ok", "status", "preflight_id", "preflight_record_digest", "target_reference", "operation", "current_version", "target_version", "installation_state", "compatibility_state", "backup_requirement", "current_installation_digest", "current_inventory_digest", "target_artifact_digest", "target_manifest_digest", "compatibility_evidence_digest", "runtime_schema_digest", "lifecycle_policy_digest", "issue_codes", "issue_count", "preflight_acceptable", "backup_must_precede_mutation", "migration_preview_required", "operator_review_phrase", "content_free", "installation_authorized", "upgrade_authorized", "backup_execution_authorized", "restore_authorized", "rollback_authorized", "old_authority_reusable")
_PROPOSAL_PUBLIC = ("ok", "status", "proposal_id", "proposal_record_digest", "preflight_id", "preflight_record_digest", "target_reference", "operation", "current_version", "target_version", "current_target_digest", "backup_evidence_digest", "backup_manifest_digest", "backup_restore_verification_digest", "migration_preview_digest", "verification_plan_digest", "rollback_plan_digest", "rollback_target_digest", "disk_space_evidence_digest", "estimated_change_count", "stages", "issue_codes", "issue_count", "backup_verified", "rollback_feasible", "migration_reversible", "proposal_acceptable", "operator_review_phrase", "content_free", "installation_authorized", "upgrade_authorized", "backup_execution_authorized", "restore_authorized", "rollback_authorized", "old_authority_reusable")
_REVIEW_PUBLIC = ("ok", "status", "review_id", "review_record_digest", "proposal_id", "proposal_record_digest", "target_reference", "operation", "disposition", "proposal_interpretation_accepted", "operator_follow_up_required", "fresh_installation_authority_still_required", "installation_authorized_by_review", "upgrade_authorized_by_review", "restore_authorized_by_review", "rollback_authorized_by_review", "content_free", "old_authority_reusable")
_RECOVERY_PUBLIC = ("ok", "status", "assessment_id", "assessment_record_digest", "proposal_id", "proposal_record_digest", "proposal_review_id", "proposal_review_digest", "target_reference", "operation", "observed_state", "transaction_evidence_digest", "observed_target_digest", "observed_backup_digest", "completed_stage_count", "evidence_complete", "recommended_action", "issue_codes", "issue_count", "resume_proposal_only", "rollback_proposal_only", "automatic_resume_permitted", "automatic_rollback_permitted", "operator_review_phrase", "content_free", "resume_authorized", "rollback_authorized", "old_authority_reusable")
_RECOVERY_REVIEW_PUBLIC = ("ok", "status", "review_id", "review_record_digest", "assessment_id", "assessment_record_digest", "proposal_id", "target_reference", "disposition", "recovery_interpretation_acknowledged", "recommended_action", "resume_authority_created", "rollback_authority_created", "fresh_exact_recovery_authority_still_required", "content_free", "old_authority_reusable")


def _public_list(directory: str, seal_field: str, keys: Iterable[str], plural: str, runtime_root=None) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    root = _dir(directory, runtime_root)
    if root.exists():
        for path in sorted(root.glob("*.json"))[-MAX_RECORDS:]:
            row = _read_json(path)
            if row and _valid(row, seal_field):
                rows.append(_project(row, keys))
    return {"ok": True, "status": f"installation_lifecycle_{plural}_ready", f"{plural[:-1]}_count": len(rows), plural: rows, **_base()}


def public_installation_lifecycle_preflights(*, runtime_root=None) -> dict[str, Any]:
    return _public_list("installation_lifecycle_preflights", "preflight_record_digest", _PREFLIGHT_PUBLIC, "preflights", runtime_root)


def public_installation_lifecycle_proposals(*, runtime_root=None) -> dict[str, Any]:
    return _public_list("installation_lifecycle_proposals", "proposal_record_digest", _PROPOSAL_PUBLIC, "proposals", runtime_root)


def public_installation_lifecycle_reviews(*, runtime_root=None) -> dict[str, Any]:
    return _public_list("installation_lifecycle_reviews", "review_record_digest", _REVIEW_PUBLIC, "reviews", runtime_root)


def public_installation_lifecycle_recovery_assessments(*, runtime_root=None) -> dict[str, Any]:
    return _public_list("installation_lifecycle_recovery_assessments", "assessment_record_digest", _RECOVERY_PUBLIC, "recovery_assessments", runtime_root)


def public_installation_lifecycle_recovery_reviews(*, runtime_root=None) -> dict[str, Any]:
    return _public_list("installation_lifecycle_recovery_reviews", "review_record_digest", _RECOVERY_REVIEW_PUBLIC, "recovery_reviews", runtime_root)


def installation_lifecycle_dashboard_record(*, runtime_root=None) -> dict[str, Any]:
    preflights = public_installation_lifecycle_preflights(runtime_root=runtime_root)
    proposals = public_installation_lifecycle_proposals(runtime_root=runtime_root)
    reviews = public_installation_lifecycle_reviews(runtime_root=runtime_root)
    recovery = public_installation_lifecycle_recovery_assessments(runtime_root=runtime_root)
    pending = sum(1 for row in proposals.get("proposals", []) if row.get("proposal_acceptable")) - sum(1 for row in reviews.get("reviews", []) if row.get("proposal_interpretation_accepted"))
    blocked = sum(1 for row in preflights.get("preflights", []) if not row.get("preflight_acceptable")) + sum(1 for row in recovery.get("recovery_assessments", []) if row.get("issue_count"))
    status = "blocked" if blocked else ("awaiting_review" if pending > 0 else ("ready" if preflights.get("preflight_count") else "unknown"))
    result = {
        "ok": blocked == 0,
        "status": status,
        "record_id": "installation-lifecycle-integration",
        "project_id": "installation-lifecycle",
        "panel_id": "lifecycle",
        "summary": "Content-free installation, upgrade, backup, restore, and rollback lifecycle evidence.",
        "evidence_digest": _digest({"preflights": preflights.get("preflight_count"), "proposals": proposals.get("proposal_count"), "reviews": reviews.get("review_count"), "recovery": recovery.get("recovery_assessment_count")}),
        "authority_state": "none",
        "review_required": pending > 0,
        "blocker_count": max(0, blocked),
        "risk_count": max(0, len(recovery.get("recovery_assessments", []))),
        "safe_next_action": "review_exact_lifecycle_record" if pending > 0 else "inspect_lifecycle_evidence",
        "read_only": True,
        **_base(),
    }
    result["record_digest"] = _digest(result)
    return result


def installation_lifecycle_response(row: Mapping[str, Any]) -> str:
    if not row.get("ok"):
        return f"Installation lifecycle control was blocked: {row.get('status', 'unknown')} ({row.get('reason', '')})."
    status = str(row.get("status") or "")
    if "review_recorded" in status:
        return "Recorded the exact lifecycle review. No installation, upgrade, backup, restore, rollback, migration, verification, or reuse authority was created."
    if "ready_for_operator_review" in status:
        return "Prepared content-free lifecycle evidence for operator review. Nothing was installed, upgraded, backed up, restored, rolled back, migrated, or verified."
    return "Installation lifecycle records are ready for read-only inspection."


def process_installation_lifecycle_control(user_text: str, *, runtime_root=None) -> dict[str, Any]:
    text = str(user_text or "").strip()
    match = _REVIEW_PROPOSAL.fullmatch(text)
    if match:
        row = review_installation_lifecycle_proposal(match.group("proposal"), expected_proposal_digest=match.group("digest"), disposition=match.group("decision"), exact_phrase=text, runtime_root=runtime_root)
        return {"active": True, "response": installation_lifecycle_response(row), "installation_lifecycle": row}
    match = _REVIEW_RECOVERY.fullmatch(text)
    if match:
        row = review_installation_lifecycle_recovery(match.group("assessment"), expected_assessment_digest=match.group("digest"), disposition=match.group("decision"), exact_phrase=text, runtime_root=runtime_root)
        return {"active": True, "response": installation_lifecycle_response(row), "installation_lifecycle": row}
    for regex, factory in (
        (_SHOW_REGISTRY, lifecycle_operation_registry),
        (_SHOW_PREFLIGHTS, public_installation_lifecycle_preflights),
        (_SHOW_PROPOSALS, public_installation_lifecycle_proposals),
        (_SHOW_REVIEWS, public_installation_lifecycle_reviews),
        (_SHOW_RECOVERY, public_installation_lifecycle_recovery_assessments),
        (_SHOW_RECOVERY_REVIEWS, public_installation_lifecycle_recovery_reviews),
    ):
        if regex.fullmatch(text):
            row = factory(runtime_root=runtime_root) if factory is not lifecycle_operation_registry else factory()
            return {"active": True, "response": installation_lifecycle_response(row), "installation_lifecycle": row}
    return {"active": False}


def render_installation_lifecycle_dashboard_html(*, runtime_root=None) -> str:
    record = installation_lifecycle_dashboard_record(runtime_root=runtime_root)
    registry = lifecycle_operation_registry()
    cards = "".join(
        f"<article class='lifecycle-card'><h2>{row['operation'].title()}</h2><p>Backup: {row['backup_requirement']}</p><p>Fresh exact authority required.</p></article>"
        for row in registry["operations"]
    )
    return (
        "<!doctype html><html><head><meta charset='utf-8'><title>Eidolon Lifecycle Integration</title>"
        "<style>body{font-family:system-ui;background:#080b10;color:#e8eef7;margin:0;padding:28px}.deck{max-width:1180px;margin:auto}"
        ".banner,.lifecycle-card{border:1px solid #284a69;border-radius:14px;background:#0c1723;padding:18px}.grid{display:grid;grid-template-columns:repeat(4,1fr);gap:14px}"
        ".muted{color:#9eb0c2}.safe{color:#61d9c4}code{color:#9fd0ff}</style></head><body><main class='deck'>"
        "<section class='banner'><h1>Installation Lifecycle Integration</h1>"
        f"<p>Status: <strong>{record['status']}</strong></p>"
        "<p class='safe'>GET-only inspection. No installation, upgrade, backup, restore, rollback, migration, verification, or approval authority is granted.</p>"
        "<p class='muted'>Every mutating stage requires separate exact digest-bound authority.</p></section>"
        f"<section class='grid'>{cards}</section>"
        "<section class='banner'><h2>Read-only surfaces</h2><code>/api/cognition/installation-lifecycle-registry</code><br>"
        "<code>/api/cognition/installation-lifecycle-preflights</code><br><code>/api/cognition/installation-lifecycle-proposals</code><br>"
        "<code>/api/cognition/installation-lifecycle-recovery-assessments</code></section></main></body></html>"
    )


def build_installation_lifecycle_integration_contract() -> dict[str, Any]:
    retained_modules = (
        "release_installation_preview",
        "release_installation_plan",
        "release_installation_staging",
        "release_installation_transaction",
        "release_installation_recovery",
        "release_installed_state",
        "runtime_lifecycle_migration",
    )
    available = []
    for module_name in retained_modules:
        try:
            __import__(f"conscious_agent.{module_name}")
            available.append(module_name)
        except ImportError:
            try:
                __import__(module_name)
                available.append(module_name)
            except ImportError:
                pass
    return {
        "ok": len(available) == len(retained_modules),
        "status": "installation_lifecycle_integration_contract_ready" if len(available) == len(retained_modules) else "installation_lifecycle_integration_contract_blocked",
        "contract_version": CONTRACT_VERSION,
        "milestone_name": MILESTONE_NAME,
        "roadmap_path": ROADMAP_PATH,
        "retained_lifecycle_module_count": len(available),
        "retained_lifecycle_modules": available,
        "exact_target_version_artifact_manifest_binding": True,
        "backup_before_existing_installation_mutation": True,
        "migration_preview_and_reversibility_required": True,
        "verification_plan_required": True,
        "rollback_bound_to_exact_backup_and_target": True,
        "interrupted_state_recovery_is_proposal_only": True,
        "ordinary_chat_exact_reviews": True,
        "cli_inspection": True,
        "get_only_api_inspection": True,
        "dashboard_read_model_available": True,
        "stale_tamper_replay_privacy_adversarial_hardening_required": True,
        **_base(),
    }
