from __future__ import annotations

"""Read-only v1197.2 runtime migration and installation foundations checkpoint."""

import hashlib
from pathlib import Path
from typing import Any

from checkpoint_registry import inspect_checkpoint_registry
from package_integrity import package_privacy_summary_for_root
from runtime_lifecycle_migration import LIFECYCLE_OPERATIONS, _digest, assess_runtime_lifecycle, create_lifecycle_evidence, create_lifecycle_plan, public_runtime_lifecycle_summary

CONTRACT_VERSION = "v1197.2"


def _d(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def _records(plan: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    previous = ""
    for sequence, operation in enumerate(LIFECYCLE_OPERATIONS, 1):
        row = create_lifecycle_evidence(
            lifecycle_id=plan["lifecycle_id"], evidence_id=f"lifecycle-{operation}-{sequence}", operation=operation,
            sequence=sequence, snapshot_digest=plan["snapshot_digest"], context_digest=plan["context_digest"],
            source_version=plan["source_version"], target_version=plan["target_version"],
            source_schema_version=plan["source_schema_version"], target_schema_version=plan["target_schema_version"],
            input_runtime_digest=plan["source_runtime_digest"], output_runtime_digest=_d(f"output:{operation}"),
            backup_digest=plan["expected_backup_digest"], rollback_digest=plan["expected_rollback_digest"],
            manifest_digest=_d(f"manifest:{operation}"), artifact_digest=_d(f"artifact:{operation}"),
            receipt_digest=_d(f"receipt:{operation}"), previous_evidence_digest=previous,
            estimated_runtime_bytes=5_000_000, estimated_evidence_bytes=10_000,
            purpose_code=f"operator_{operation}_foundation_review",
        )
        rows.append(row)
        previous = row["evidence_digest"]
    return rows


def build_runtime_lifecycle_migration_checkpoint(
    *, source_root: str | Path | None = None, runtime_root: str | Path | None = None
) -> dict[str, Any]:
    source = Path(source_root or Path(__file__).resolve().parents[1]).resolve()
    runtime = Path(runtime_root).resolve() if runtime_root else None
    checks: list[bool] = []
    def require(value: object) -> None: checks.append(bool(value))

    snapshot = _d("v1197.2:snapshot")
    context = _d("v1197.2:context")
    plan = create_lifecycle_plan(
        lifecycle_id="runtime-lifecycle-foundations-0001", snapshot_digest=snapshot, context_digest=context,
        source_version="1196.9", target_version="1197.2", source_schema_version="1.0", target_schema_version="2.0",
        source_runtime_digest=_d("source-runtime"), expected_backup_digest=_d("backup"),
        expected_rollback_digest=_d("rollback"), purpose_code="operator_runtime_lifecycle_foundation_review",
        max_records=8, max_evidence_bytes=1_000_000, max_runtime_bytes=10_000_000,
    )
    rows = _records(plan)
    verification = {"content_free": True, "current_regressions_separate": True, "inherited_debt_visible": True, "global_profile_pass_claimed": False}
    assessment = assess_runtime_lifecycle(plan, rows, current_snapshot_digest=snapshot, current_context_digest=context, verification_summary=verification)
    summary = public_runtime_lifecycle_summary(assessment)

    require(assessment["status"] == "ready_for_operator_review")
    require(not assessment["errors"])
    require(summary["operation_count"] == len(LIFECYCLE_OPERATIONS))
    require(summary["operations"] == list(LIFECYCLE_OPERATIONS))
    for field in ("exact_lineage_verified", "backup_truth_preserved", "rollback_truth_preserved", "original_runtime_preserved", "fresh_install_isolated", "content_free"):
        require(summary[field] is True)
    for field in ("runtime_read", "backup_created", "migration_applied", "upgrade_applied", "rollback_applied", "fresh_install_performed", "files_written", "files_deleted", "runtime_mutated", "source_modified", "provider_contacted", "model_contacted", "thread_started", "process_started", "approval_created", "approval_consumed", "automatic_continuation", "global_profile_pass_claimed"):
        require(summary[field] is False)
    require(summary["authority_state"] == "separate_not_granted")

    blocked: dict[str, list[str]] = {}
    mutations: dict[str, tuple[str, Any]] = {
        "duplicate-id": ("evidence_id", rows[0]["evidence_id"]),
        "broken-lineage": ("previous_evidence_digest", _d("broken")),
        "stale-snapshot": ("snapshot_digest", _d("stale")),
        "stale-context": ("context_digest", _d("stale-context")),
        "unsupported-operation": ("operation", "arbitrary_install"),
        "unsupported-state": ("lifecycle_state", "running"),
        "malformed-digest": ("manifest_digest", "bad"),
        "private-field": ("secret", "redacted"),
        "backup-truth": ("backup_digest", _d("wrong-backup")),
        "rollback-truth": ("rollback_digest", _d("wrong-rollback")),
        "runtime-loss": ("original_runtime_preserved", False),
        "fresh-install-isolation": ("fresh_install_isolated", False),
        "runtime-read": ("runtime_read", True),
        "backup-created": ("backup_created", True),
        "migration-applied": ("migration_applied", True),
        "upgrade-applied": ("upgrade_applied", True),
        "rollback-applied": ("rollback_applied", True),
        "fresh-install-performed": ("fresh_install_performed", True),
        "files-written": ("files_written", True),
        "files-deleted": ("files_deleted", True),
        "runtime-mutation": ("runtime_mutated", True),
        "source-mutation": ("source_modified", True),
        "provider-contact": ("provider_contacted", True),
        "thread-start": ("thread_started", True),
        "process-start": ("process_started", True),
        "approval": ("approval_created", True),
        "automatic-continuation": ("automatic_continuation", True),
        "authority": ("authority_state", "granted"),
    }
    for name, (field, value) in mutations.items():
        candidates = [dict(row) for row in rows]
        index = 1 if name == "duplicate-id" else (len(candidates) - 1 if name == "fresh-install-isolation" else 0)
        candidates[index][field] = value
        candidates[index]["evidence_digest"] = _digest({key: item for key, item in candidates[index].items() if key != "evidence_digest"})
        result = assess_runtime_lifecycle(plan, candidates, current_snapshot_digest=snapshot, current_context_digest=context, verification_summary=verification)
        require(result["status"] == "blocked"); require(bool(result["errors"])); blocked[name] = result["errors"]

    oversized_plan = dict(plan); oversized_plan["max_records"] = 4
    oversized_plan["plan_digest"] = _digest({key: value for key, value in oversized_plan.items() if key != "plan_digest"})
    result = assess_runtime_lifecycle(oversized_plan, rows, current_snapshot_digest=snapshot, current_context_digest=context, verification_summary=verification)
    require(result["status"] == "blocked"); require("oversized_evidence" in result["errors"]); blocked["oversized"] = result["errors"]

    privacy = package_privacy_summary_for_root(source)
    require(privacy.get("ok") is True)
    registry = inspect_checkpoint_registry(source_root=source)
    descriptor = next((row for row in registry["checkpoints"] if row["checkpoint_id"] == "runtime-lifecycle-migration-checkpoint"), None)
    require(bool(descriptor)); require((descriptor or {}).get("contract_version") == CONTRACT_VERSION)
    require((descriptor or {}).get("builder") == "build_runtime_lifecycle_migration_checkpoint")
    require((descriptor or {}).get("read_only") is True); require((descriptor or {}).get("post_available") is False)
    require(runtime is None or not runtime.exists())

    return {
        "ok": all(checks), "checkpoint_id": "runtime-lifecycle-migration:v1197.2", "contract_version": CONTRACT_VERSION,
        "passed": sum(checks), "total": len(checks), "read_only": True, "post_available": False,
        "content_free": True, "source_unchanged": True, "runtime_mutated": False, "production_source_modified": False,
        "runtime_read": False, "backup_created": False, "migration_applied": False, "upgrade_applied": False,
        "rollback_applied": False, "fresh_install_performed": False, "files_written": False, "files_deleted": False,
        "approval_created": False, "approval_consumed": False, "provider_contacted": False, "model_contacted": False,
        "thread_started": False, "process_started": False, "automatic_continuation": False,
        "global_profile_pass_claimed": False, "authority_granted": False,
        "summary": summary, "blocked_cases": blocked,
        "limitations": [
            "Evidence-only foundations; no runtime data is read, copied, migrated, upgraded, restored, or installed.",
            "Backup and rollback truth is digest-bound but no backup artifact is materialized in this bundle.",
            "Operator approval and lifecycle application remain deferred to v1197.3-v1197.5.",
            "Interruption, stale backup, partial upgrade, rollback failure, and fresh-install reliability remain deferred to v1197.6-v1197.8.",
            "No installation, promotion, certification, publication, release, or autonomous authority is granted.",
        ],
    }
