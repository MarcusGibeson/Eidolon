from __future__ import annotations

"""Read-only v1197.9 runtime lifecycle checkpoint.

This checkpoint consolidates the v1197 migration/backup/upgrade/rollback/fresh-
install foundations, operator-reviewed lifecycle application, and lifecycle
reliability/adversarial evidence. It reads source-declared, content-free
checkpoint output only. It performs no runtime read, backup creation, migration,
upgrade, rollback, installation, recovery, retry, provider/model contact,
process/thread start, approval mutation, source/runtime mutation, promotion,
certification, publication, release, or authority expansion.
"""

import hashlib
import json
import os
from pathlib import Path
from typing import Any, Mapping

from checkpoint_registry import inspect_checkpoint_registry
from package_integrity import package_privacy_summary_for_root
from runtime_lifecycle_application_review import DECISIONS, REVIEW_ACTIONS
from runtime_lifecycle_application_review_checkpoint import build_runtime_lifecycle_application_review_checkpoint
from runtime_lifecycle_migration import LIFECYCLE_OPERATIONS
from runtime_lifecycle_migration_checkpoint import build_runtime_lifecycle_migration_checkpoint
from runtime_lifecycle_reliability_adversarial import EVENT_CLASSES as RELIABILITY_EVENT_CLASSES
from runtime_lifecycle_reliability_adversarial_checkpoint import build_runtime_lifecycle_reliability_adversarial_checkpoint

CONTRACT_VERSION = "v1197.9"
_CHECKPOINT_ID = "runtime-lifecycle-checkpoint"
_EXCLUDED_DIRS = {
    "data", "sandbox", ".git", ".venv", "venv", "__pycache__",
    ".pytest_cache", ".mypy_cache", ".ruff_cache", "dist", "build", "reports",
}
_PRIVATE_KEYS = {
    "prompt", "conversation", "message", "memory", "secret", "raw_source",
    "source_text", "patch", "patch_text", "stdout", "stderr",
    "provider_payload", "private_reasoning", "credential", "token_value",
    "runtime_payload", "backup_payload", "rollback_payload",
}
_LIMITATIONS = (
    "Lifecycle evidence is source-declared and content-free; no runtime data is read, copied, migrated, upgraded, restored, or installed.",
    "Approve, reject, and defer remain presentation-only; no application authorization or approval is created or consumed.",
    "Reliability and recovery outcomes remain evidence-only; no recovery, retry, rollback response, or lifecycle operation is executed.",
    "Inherited global-profile performance and partial-fixture-overlap debt remains explicit and unresolved.",
    "Feature freeze, architecture consolidation, performance hardening, documentation completion, and verifier reconciliation continue in v1198; Desktop Codex and native-provider review remain scheduled for v1200.",
)


def _digest(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str).encode("utf-8")
    ).hexdigest()


def _tree_signature(root: Path) -> tuple[str, int]:
    digest = hashlib.sha256()
    paths: list[Path] = []
    for base, dirs, files in os.walk(root):
        dirs[:] = [name for name in dirs if name not in _EXCLUDED_DIRS]
        for name in files:
            path = Path(base) / name
            if path.suffix.lower() not in {".pyc", ".pyo"}:
                paths.append(path)
    for path in sorted(paths):
        try:
            relative = path.relative_to(root).as_posix()
            data = path.read_bytes()
        except OSError:
            continue
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(hashlib.sha256(data).digest())
    return digest.hexdigest(), len(paths)


def _private_fields(snapshot: Mapping[str, Any]) -> list[str]:
    return sorted(
        str(key) for key in snapshot
        if any(token in str(key).lower() for token in _PRIVATE_KEYS)
    )


def _validate_snapshot(snapshot: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []
    errors.extend(f"private_field:{field}" for field in _private_fields(snapshot))

    expected_true = (
        "content_free", "read_only", "privacy_preserved",
        "authority_boundary_preserved", "original_runtime_preserved",
        "backup_truth_preserved", "rollback_truth_preserved",
        "fresh_install_isolated", "existing_runtime_untouched",
        "exact_lineage_verified", "operator_review_accountable",
        "foreground_available", "recovery_review_required",
        "historical_truth_preserved", "current_regressions_separate",
        "inherited_debt_visible",
    )
    expected_false = (
        "runtime_read", "backup_created", "migration_applied", "upgrade_applied",
        "rollback_applied", "fresh_install_performed", "files_written",
        "files_deleted", "automatic_recovery", "automatic_retry",
        "recovery_executed", "retry_executed", "operation_executed",
        "application_authorized", "approval_created", "approval_consumed",
        "runtime_mutated", "production_source_modified", "provider_contacted",
        "model_contacted", "thread_started", "process_started",
        "installation_performed", "promotion_performed",
        "certification_performed", "publication_performed", "release_performed",
        "automatic_continuation", "global_profile_pass_claimed", "authority_granted",
    )
    for field in expected_true:
        if snapshot.get(field) is not True:
            errors.append(f"invalid_{field}")
    for field in expected_false:
        if snapshot.get(field) is not False:
            errors.append(f"invalid_{field}")

    if snapshot.get("authority_state") != "separate_not_granted":
        errors.append("authority_expansion")
    if snapshot.get("foundation_contract_version") != "v1197.2":
        errors.append("foundation_contract_drift")
    if snapshot.get("review_contract_version") != "v1197.5":
        errors.append("review_contract_drift")
    if snapshot.get("reliability_contract_version") != "v1197.8":
        errors.append("reliability_contract_drift")

    expected_counts = {
        "retained_checkpoint_count": 3,
        "operation_count": 5,
        "review_action_count": 5,
        "decision_count": 3,
        "review_count": 15,
        "reliability_event_class_count": 8,
    }
    for field, expected in expected_counts.items():
        if snapshot.get(field) != expected:
            errors.append(f"invalid_{field}")

    body = {key: value for key, value in snapshot.items() if key != "checkpoint_digest"}
    if snapshot.get("checkpoint_digest") != _digest(body):
        errors.append("checkpoint_tamper")
    return sorted(set(errors))


def build_runtime_lifecycle_checkpoint(
    *, source_root: str | Path | None = None, runtime_root: str | Path | None = None
) -> dict[str, Any]:
    source = Path(source_root or Path(__file__).resolve().parents[1]).expanduser().resolve()
    del runtime_root
    before_digest, before_count = _tree_signature(source)
    checks: list[bool] = []

    def require(value: object) -> None:
        checks.append(bool(value))

    foundations = build_runtime_lifecycle_migration_checkpoint(source_root=source)
    review = build_runtime_lifecycle_application_review_checkpoint(source_root=source)
    reliability = build_runtime_lifecycle_reliability_adversarial_checkpoint(source_root=source)

    retained = (
        (foundations, "v1197.2", 94, 5),
        (review, "v1197.5", 306, 5),
        (reliability, "v1197.8", 420, 4),
    )
    for report, version, total, limitation_count in retained:
        require(report.get("ok") is True)
        require(report.get("contract_version") == version)
        require(report.get("passed") == report.get("total") == total)
        require(bool(report.get("summary")))
        require(bool(report.get("blocked_cases")))
        require(len(report.get("limitations") or []) == limitation_count)
        for blocked in (report.get("blocked_cases") or {}).values():
            require(bool(blocked))

    foundation_summary = dict(foundations.get("summary") or {})
    review_summary = dict(review.get("summary") or {})
    reliability_summary = dict(reliability.get("summary") or {})

    snapshot: dict[str, Any] = {
        "contract_version": CONTRACT_VERSION,
        "checkpoint_id": "runtime-lifecycle:v1197.9",
        "foundation_contract_version": foundations.get("contract_version"),
        "review_contract_version": review.get("contract_version"),
        "reliability_contract_version": reliability.get("contract_version"),
        "retained_checkpoint_count": 3,
        "operation_count": len(LIFECYCLE_OPERATIONS),
        "operations": list(LIFECYCLE_OPERATIONS),
        "review_action_count": len(REVIEW_ACTIONS),
        "decision_count": len(DECISIONS),
        "decisions": list(DECISIONS),
        "review_count": review_summary.get("review_count", 0),
        "reliability_event_class_count": len(RELIABILITY_EVENT_CLASSES),
        "reliability_event_classes": list(RELIABILITY_EVENT_CLASSES),
        "content_free": True,
        "read_only": True,
        "privacy_preserved": True,
        "authority_boundary_preserved": all(
            summary.get("authority_state") == "separate_not_granted"
            for summary in (foundation_summary, review_summary, reliability_summary)
        ),
        "original_runtime_preserved": all(
            summary.get("original_runtime_preserved") is True
            for summary in (foundation_summary, review_summary, reliability_summary)
        ),
        "backup_truth_preserved": all(
            summary.get("backup_truth_preserved") is True
            for summary in (foundation_summary, review_summary, reliability_summary)
        ),
        "rollback_truth_preserved": all(
            summary.get("rollback_truth_preserved") is True
            for summary in (foundation_summary, review_summary, reliability_summary)
        ),
        "fresh_install_isolated": (
            foundation_summary.get("fresh_install_isolated") is True
            and review_summary.get("fresh_install_isolation_preserved") is True
        ),
        "existing_runtime_untouched": reliability_summary.get("existing_runtime_untouched") is True,
        "exact_lineage_verified": all(
            summary.get("exact_lineage_verified") is True
            for summary in (foundation_summary, review_summary, reliability_summary)
        ),
        "operator_review_accountable": (
            review_summary.get("all_reviews_valid") is True
            and review_summary.get("review_count") == len(LIFECYCLE_OPERATIONS) * len(DECISIONS)
        ),
        "foreground_available": reliability_summary.get("foreground_available") is True,
        "recovery_review_required": reliability_summary.get("recovery_review_required") is True,
        "historical_truth_preserved": True,
        "current_regressions_separate": True,
        "inherited_debt_visible": True,
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
        "recovery_executed": False,
        "retry_executed": False,
        "operation_executed": False,
        "application_authorized": False,
        "approval_created": False,
        "approval_consumed": False,
        "runtime_mutated": False,
        "production_source_modified": False,
        "provider_contacted": False,
        "model_contacted": False,
        "thread_started": False,
        "process_started": False,
        "installation_performed": False,
        "promotion_performed": False,
        "certification_performed": False,
        "publication_performed": False,
        "release_performed": False,
        "automatic_continuation": False,
        "global_profile_pass_claimed": False,
        "authority_state": "separate_not_granted",
        "authority_granted": False,
    }
    snapshot["checkpoint_digest"] = _digest(snapshot)
    errors = _validate_snapshot(snapshot)
    require(not errors)

    mutation_cases: dict[str, dict[str, Any]] = {
        "private-field": {"runtime_payload": "forbidden"},
        "foundation-contract-drift": {"foundation_contract_version": "v1197.1"},
        "review-contract-drift": {"review_contract_version": "v1197.4"},
        "reliability-contract-drift": {"reliability_contract_version": "v1197.7"},
        "retained-count": {"retained_checkpoint_count": 2},
        "operation-count": {"operation_count": 4},
        "review-action-count": {"review_action_count": 4},
        "decision-count": {"decision_count": 2},
        "review-count": {"review_count": 14},
        "reliability-event-count": {"reliability_event_class_count": 7},
        "privacy-loss": {"privacy_preserved": False},
        "authority-boundary-loss": {"authority_boundary_preserved": False},
        "runtime-loss": {"original_runtime_preserved": False},
        "backup-truth-loss": {"backup_truth_preserved": False},
        "rollback-truth-loss": {"rollback_truth_preserved": False},
        "fresh-install-isolation-loss": {"fresh_install_isolated": False},
        "runtime-touched": {"existing_runtime_untouched": False},
        "lineage-loss": {"exact_lineage_verified": False},
        "review-accountability-loss": {"operator_review_accountable": False},
        "foreground-block": {"foreground_available": False},
        "recovery-review-loss": {"recovery_review_required": False},
        "historical-truth-loss": {"historical_truth_preserved": False},
        "verification-boundary-loss": {"current_regressions_separate": False},
        "debt-hidden": {"inherited_debt_visible": False},
        "runtime-read": {"runtime_read": True},
        "backup-created": {"backup_created": True},
        "migration-applied": {"migration_applied": True},
        "upgrade-applied": {"upgrade_applied": True},
        "rollback-applied": {"rollback_applied": True},
        "fresh-install": {"fresh_install_performed": True},
        "files-written": {"files_written": True},
        "files-deleted": {"files_deleted": True},
        "automatic-recovery": {"automatic_recovery": True},
        "automatic-retry": {"automatic_retry": True},
        "recovery-execution": {"recovery_executed": True},
        "retry-execution": {"retry_executed": True},
        "operation-execution": {"operation_executed": True},
        "application-authority": {"application_authorized": True},
        "approval-create": {"approval_created": True},
        "approval-consume": {"approval_consumed": True},
        "runtime-mutation": {"runtime_mutated": True},
        "source-mutation": {"production_source_modified": True},
        "provider-contact": {"provider_contacted": True},
        "model-contact": {"model_contacted": True},
        "thread-start": {"thread_started": True},
        "process-start": {"process_started": True},
        "installation": {"installation_performed": True},
        "promotion": {"promotion_performed": True},
        "certification": {"certification_performed": True},
        "publication": {"publication_performed": True},
        "release": {"release_performed": True},
        "automatic-continuation": {"automatic_continuation": True},
        "global-pass-claim": {"global_profile_pass_claimed": True},
        "authority-state": {"authority_state": "granted"},
        "authority": {"authority_granted": True},
    }
    blocked_cases: dict[str, list[str]] = {}
    for name, changes in mutation_cases.items():
        candidate = dict(snapshot)
        candidate.update(changes)
        candidate["checkpoint_digest"] = _digest({k: v for k, v in candidate.items() if k != "checkpoint_digest"})
        case_errors = _validate_snapshot(candidate)
        require(bool(case_errors))
        blocked_cases[name] = case_errors

    tampered = dict(snapshot)
    tampered["checkpoint_digest"] = "0" * 64
    tamper_errors = _validate_snapshot(tampered)
    require("checkpoint_tamper" in tamper_errors)
    blocked_cases["tamper"] = tamper_errors

    privacy = package_privacy_summary_for_root(source)
    require(privacy.get("ok") is True)
    registry = inspect_checkpoint_registry(source_root=source)
    descriptor = next(
        (row for row in registry["checkpoints"] if row["checkpoint_id"] == _CHECKPOINT_ID),
        None,
    )
    require(descriptor is not None)
    require((descriptor or {}).get("contract_version") == CONTRACT_VERSION)
    require((descriptor or {}).get("builder") == "build_runtime_lifecycle_checkpoint")
    require((descriptor or {}).get("read_only") is True)
    require((descriptor or {}).get("post_available") is False)
    require((descriptor or {}).get("required_input_count") == 0)
    require(not registry["duplicate_checkpoint_ids"])
    require(not registry["duplicate_builder_targets"])

    after_digest, after_count = _tree_signature(source)
    require(after_digest == before_digest)
    require(after_count == before_count)

    summary = dict(snapshot)
    summary["blocked_case_count"] = len(blocked_cases)
    return {
        "ok": all(checks),
        "checkpoint_id": "runtime-lifecycle:v1197.9",
        "contract_version": CONTRACT_VERSION,
        "read_only": True,
        "post_available": False,
        "content_free": True,
        "source_unchanged": after_digest == before_digest and after_count == before_count,
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
        "automatic_recovery": False,
        "automatic_retry": False,
        "recovery_executed": False,
        "retry_executed": False,
        "operation_executed": False,
        "application_authorized": False,
        "approval_created": False,
        "approval_consumed": False,
        "provider_contacted": False,
        "model_contacted": False,
        "thread_started": False,
        "process_started": False,
        "installation_performed": False,
        "promotion_performed": False,
        "certification_performed": False,
        "publication_performed": False,
        "release_performed": False,
        "automatic_continuation": False,
        "global_profile_pass_claimed": False,
        "authority_granted": False,
        "passed": sum(checks),
        "total": len(checks),
        "summary": summary,
        "retained_checkpoints": {
            "foundations": {
                "contract_version": foundations.get("contract_version"),
                "passed": foundations.get("passed"), "total": foundations.get("total"),
            },
            "review": {
                "contract_version": review.get("contract_version"),
                "passed": review.get("passed"), "total": review.get("total"),
            },
            "reliability": {
                "contract_version": reliability.get("contract_version"),
                "passed": reliability.get("passed"), "total": reliability.get("total"),
            },
        },
        "blocked_cases": blocked_cases,
        "privacy": privacy,
        "limitations": list(_LIMITATIONS),
    }
