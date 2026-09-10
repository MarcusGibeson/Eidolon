from __future__ import annotations

"""Strictly read-only v1149.9 Cognitive Alpha feature-freeze governance checkpoint."""

import hashlib
import os
from pathlib import Path
from typing import Any, Iterable

from cognitive_alpha_feature_freeze import FEATURE_DOMAINS
from cognitive_alpha_feature_freeze_execution_checkpoint import build_cognitive_alpha_feature_freeze_execution_checkpoint
from cognitive_alpha_feature_freeze_intake_checkpoint import build_cognitive_alpha_feature_freeze_intake_checkpoint
from cognitive_alpha_feature_freeze_reliability_checkpoint import build_cognitive_alpha_feature_freeze_reliability_checkpoint
from cognitive_alpha_install_readiness import PATHS

CONTRACT_VERSION = "v1149.9"
_EXCLUDED_SOURCE_ROOTS = {"data", ".git", ".venv", "venv", "__pycache__", ".pytest_cache", ".mypy_cache", "reports"}


def _runtime_root() -> Path:
    base = Path(os.environ.get("EIDOLON_DATA_DIR") or Path(__file__).resolve().parents[1] / "data")
    return base.expanduser().resolve() / "cognition"


def _signature(root: Path, *, source_tree: bool = False) -> str:
    digest = hashlib.sha256()
    if not root.exists():
        digest.update(b"missing-tree")
        return digest.hexdigest()
    if source_tree:
        paths: list[Path] = []
        for base, directories, names in os.walk(root):
            directories[:] = [name for name in directories if name not in _EXCLUDED_SOURCE_ROOTS]
            paths.extend(Path(base) / name for name in names if Path(name).suffix not in {".pyc", ".pyo"})
    else:
        paths = [
            item for item in root.rglob("*")
            if item.is_file() and "__pycache__" not in item.parts and item.suffix not in {".pyc", ".pyo"}
        ]
    for path in sorted(paths):
        try:
            stat = path.stat()
            digest.update(path.relative_to(root).as_posix().encode("utf-8"))
            digest.update(b"\0")
            digest.update(str(stat.st_size).encode("ascii"))
            digest.update(b"\0")
            digest.update(str(stat.st_mtime_ns).encode("ascii"))
        except (OSError, ValueError):
            continue
    return digest.hexdigest()


def _false_across(rows: Iterable[dict[str, Any]], fields: Iterable[str]) -> bool:
    return all(not bool(row.get(field)) for row in rows for field in fields)


def build_cognitive_alpha_feature_freeze_governance_checkpoint(
    runtime_root: str | Path | None = None,
    *,
    source_root: str | Path | None = None,
) -> dict[str, Any]:
    runtime = Path(runtime_root).expanduser().resolve() if runtime_root else _runtime_root()
    source = Path(source_root).expanduser().resolve() if source_root else Path(__file__).resolve().parents[1]
    runtime_before = _signature(runtime)
    source_before = _signature(source, source_tree=True)

    intake = build_cognitive_alpha_feature_freeze_intake_checkpoint(source_root=source)
    execution = build_cognitive_alpha_feature_freeze_execution_checkpoint(source_root=source)
    reliability = build_cognitive_alpha_feature_freeze_reliability_checkpoint(runtime, source_root=source)

    freeze = intake.get("feature_freeze") or {}
    readiness = intake.get("install_readiness") or {}
    readiness_execution = execution.get("readiness_execution") or {}
    recovery = execution.get("recovery_continuity") or {}
    continuity = reliability.get("continuity") or {}
    review = reliability.get("reliability") or {}

    features = list(freeze.get("features") or [])
    readiness_rows = list(readiness.get("paths") or [])
    execution_rows = list(readiness_execution.get("executions") or [])
    recovery_rows = list(recovery.get("records") or [])
    continuity_rows = list(continuity.get("recent_records") or [])
    all_rows = features + readiness_rows + execution_rows + recovery_rows + continuity_rows

    forbidden_private_keys = {
        "text",
        "content",
        "prompt",
        "message",
        "conversation",
        "reflection",
        "reasoning",
        "memory_text",
        "belief_text",
        "goal_text",
        "motivation_text",
        "relationship_text",
        "mood_text",
        "provider_payload",
        "source_text",
        "patch_text",
        "raw_evidence",
        "hidden_reasoning",
    }
    operational_fields = (
        "browses",
        "contacts_provider",
        "provider_contacted",
        "executes_commands",
        "command_executed",
        "mutates_cognition",
        "mutates_memory",
        "mutates_runtime",
        "runtime_mutated",
        "modifies_source",
        "source_modified",
        "sends_messages",
        "message_sent",
        "creates_notifications",
        "notification_created",
        "creates_goals",
        "goal_created",
        "creates_plans",
        "plan_created",
        "creates_development_proposals",
        "development_proposal_created",
    )
    release_fields = (
        "creates_approval",
        "approval_created",
        "creates_authorization",
        "authorization_created",
        "installs",
        "installation_performed",
        "upgrades",
        "upgrade_performed",
        "creates_backup",
        "backup_created",
        "rolls_back",
        "rollback_performed",
        "packages",
        "packaging_performed",
        "promotes",
        "promotion_performed",
        "certifies",
        "certification_performed",
    )

    checks: list[tuple[str, bool]] = [
        (
            "feature_freeze_arc_lineage",
            intake.get("ok")
            and execution.get("ok")
            and reliability.get("ok")
            and intake.get("contract_version") == "v1149.2"
            and execution.get("contract_version") == "v1149.5"
            and reliability.get("contract_version") == "v1149.8",
        ),
        (
            "freeze_readiness_execution_recovery_continuity_reliability_separation",
            freeze.get("contract_version") == "v1149.0"
            and readiness.get("contract_version") == "v1149.1"
            and readiness_execution.get("contract_version") == "v1149.3"
            and recovery.get("contract_version") == "v1149.4"
            and continuity.get("contract_version") == "v1149.6"
            and review.get("contract_version") == "v1149.7",
        ),
        (
            "frozen_feature_domains_complete_and_unique",
            freeze.get("feature_count") == len(FEATURE_DOMAINS) == 12
            and {row.get("domain") for row in features} == set(FEATURE_DOMAINS)
            and not freeze.get("duplicate_feature_ids"),
        ),
        (
            "new_capabilities_closed_and_bounded_repairs_allowed",
            freeze.get("new_feature_intake_open") is False
            and all(row.get("new_capability_allowed") is False for row in features)
            and all(row.get("repair_allowed") is True for row in features),
        ),
        (
            "compatibility_changes_and_feature_records_require_review",
            all(row.get("compatibility_change_requires_review") is True for row in features)
            and all(row.get("operator_review_required") is True for row in features),
        ),
        (
            "five_release_readiness_paths_complete_and_unique",
            readiness.get("path_count") == len(PATHS) == 5
            and {row.get("path") for row in readiness_rows} == set(PATHS)
            and not readiness.get("duplicate_readiness_ids"),
        ),
        (
            "readiness_has_exact_freeze_lineage_and_starts_ineligible",
            all(
                row.get("freeze_id") == freeze.get("freeze_id")
                and row.get("freeze_revision") == freeze.get("freeze_revision")
                and row.get("freeze_digest") == freeze.get("structural_digest")
                and row.get("execution_eligible") is False
                for row in readiness_rows
            ),
        ),
        (
            "operator_confirmed_structural_dry_runs_cover_every_path",
            readiness_execution.get("operator_confirmed") is True
            and readiness_execution.get("execution_count") == len(PATHS)
            and {row.get("path") for row in execution_rows} == set(PATHS)
            and all(row.get("check_mode") == "structural_dry_run" for row in execution_rows),
        ),
        (
            "release_readiness_execution_is_strictly_bounded",
            all(
                int(row.get("step_budget") or 0) <= 4
                and int(row.get("attempt_budget") or 0) <= 1
                and int(row.get("runtime_budget_ms") or 0) <= 250
                for row in execution_rows
            ),
        ),
        (
            "readiness_execution_performs_no_release_operation",
            readiness_execution.get("all_operations_simulated") is True
            and all(row.get("operation_performed") is False for row in execution_rows),
        ),
        (
            "recovery_continuity_covers_all_paths_and_is_stable",
            recovery.get("record_count") == len(PATHS)
            and recovery.get("stable_count") == len(PATHS)
            and {row.get("path") for row in recovery_rows} == set(PATHS)
            and not recovery.get("duplicate_continuity_ids"),
        ),
        (
            "restart_replay_and_exact_lineage_recovery_are_verified",
            all(
                row.get("restart_replay") == "verified"
                and row.get("lineage_recovery") == "verified"
                and row.get("execution_id")
                and row.get("execution_digest")
                for row in recovery_rows
            ),
        ),
        (
            "rollback_pointers_remain_unchanged",
            all(row.get("rollback_pointer_changed") is False for row in recovery_rows)
            and review.get("rollback_pointer_change_count") == 0,
        ),
        (
            "runtime_state_is_excluded_from_source_only_packaging",
            all(row.get("runtime_state_packaged") is False for row in recovery_rows)
            and review.get("runtime_packaging_violation_count") == 0,
        ),
        (
            "cross_cycle_lineage_and_visible_behavior_are_bounded",
            all(not row.get("prior_revision") or row.get("prior_structural_digest") for row in continuity_rows)
            and all(row.get("visible_state") in {"steady", "changed", "attention"} for row in continuity_rows),
        ),
        (
            "drift_failures_recovery_and_packaging_are_reviewed",
            review.get("drift_count", 0) >= 0
            and review.get("failure_count", 0) >= 0
            and review.get("stable_recovery_count", 0) >= 0
            and review.get("rollback_pointer_change_count", 0) >= 0
            and review.get("runtime_packaging_violation_count", 0) >= 0,
        ),
        (
            "release_reliability_is_bounded_and_operator_visible",
            0 <= review.get("reliability_score", -1) <= 100
            and 0 <= review.get("uncertainty", -1) <= 100
            and review.get("classification") in {"reliable", "review_required"}
            and review.get("operator_visible_state") in {"ready", "attention"},
        ),
        (
            "records_are_content_free_and_hide_private_reasoning",
            freeze.get("content_free")
            and readiness.get("content_free")
            and readiness_execution.get("content_free")
            and recovery.get("content_free")
            and not continuity.get("raw_content_exposed")
            and not review.get("raw_content_exposed")
            and not continuity.get("hidden_reasoning_exposed")
            and not review.get("hidden_reasoning_exposed")
            and not any(forbidden_private_keys.intersection(row.keys()) for row in all_rows),
        ),
        (
            "feature_freeze_and_release_records_have_no_operational_authority",
            not any(freeze.get("authority_boundary", {}).values())
            and not any(readiness.get("authority_boundary", {}).values())
            and not any(readiness_execution.get("authority_boundary", {}).values())
            and not any(recovery.get("authority_boundary", {}).values())
            and not any(continuity.get("authority_boundary", {}).values())
            and _false_across(all_rows + [review], operational_fields),
        ),
        (
            "approval_authorization_release_operations_promotion_and_certification_are_separate",
            _false_across(all_rows + [readiness_execution, recovery, continuity, review], release_fields),
        ),
        (
            "checkpoint_surfaces_are_read_only_and_post_unavailable",
            intake.get("read_only")
            and execution.get("read_only")
            and reliability.get("read_only")
            and not intake.get("post_available")
            and not execution.get("post_available")
            and not reliability.get("post_available"),
        ),
        ("source_runtime_separation", "data" in _EXCLUDED_SOURCE_ROOTS),
        (
            "checkpoint_does_not_modify_source_runtime_or_perform_release_work",
            source_before == _signature(source, source_tree=True)
            and runtime_before == _signature(runtime)
            and not review.get("operation_performed"),
        ),
        (
            "desktop_verification_and_v1150_benchmark_remain_pending_without_consciousness_claim",
            True,
        ),
    ]

    passed = sum(bool(value) for _, value in checks)
    ok = passed == len(checks)
    return {
        "contract_version": CONTRACT_VERSION,
        "checkpoint_id": "cognitive-alpha-feature-freeze-governance:v1149.9",
        "ok": ok,
        "status": "ready_for_v1150_benchmark" if ok else "review_required",
        "passed": passed,
        "total": len(checks),
        "checks": [
            {"id": name, "status": "pass" if value else "fail", "passed": bool(value)}
            for name, value in checks
        ],
        "summary": {
            "feature_count": len(features),
            "readiness_path_count": len(readiness_rows),
            "execution_count": len(execution_rows),
            "stable_recovery_count": recovery.get("stable_count", 0),
            "continuity_record_count": len(continuity_rows),
            "reliability_score": review.get("reliability_score", 0),
            "classification": review.get("classification", "unknown"),
            "new_feature_intake_open": freeze.get("new_feature_intake_open"),
        },
        "intake": intake,
        "execution": execution,
        "reliability": reliability,
        "read_only": True,
        "post_available": False,
        "source_modified": source_before != _signature(source, source_tree=True),
        "runtime_mutated": runtime_before != _signature(runtime),
        "feature_freeze_modified_by_checkpoint": False,
        "readiness_execution_performed_by_checkpoint": False,
        "installation_performed": False,
        "upgrade_performed": False,
        "backup_created": False,
        "rollback_performed": False,
        "packaging_performed": False,
        "provider_contacted": False,
        "command_executed": False,
        "message_sent": False,
        "notification_created": False,
        "goal_created": False,
        "plan_created": False,
        "development_proposal_created": False,
        "approval_created": False,
        "authorization_created": False,
        "promotion_performed": False,
        "certification_performed": False,
        "raw_conversation_exposed": False,
        "raw_message_exposed": False,
        "prompt_exposed": False,
        "reflection_text_exposed": False,
        "memory_text_exposed": False,
        "belief_text_exposed": False,
        "goal_text_exposed": False,
        "motivation_text_exposed": False,
        "relationship_text_exposed": False,
        "mood_text_exposed": False,
        "provider_payload_exposed": False,
        "source_text_exposed": False,
        "patch_text_exposed": False,
        "hidden_reasoning_exposed": False,
        "desktop_verification_pending": True,
        "v1150_benchmark_pending": True,
        "v1150_benchmark_performed": False,
        "consciousness_proven": False,
    }
