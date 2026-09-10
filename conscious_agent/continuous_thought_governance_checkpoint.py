from __future__ import annotations

"""Strictly read-only v1127.9 Continuous Thought Governance checkpoint."""

import hashlib
import os
from pathlib import Path
from typing import Any

from continuous_thought_deliberation_checkpoint import build_continuous_thought_deliberation_checkpoint
from continuous_thought_intake_checkpoint import build_continuous_thought_intake_checkpoint
from continuous_thought_integration_checkpoint import build_continuous_thought_integration_checkpoint
from continuous_thought_threads import STATES
from thought_thread_arbitration import OUTCOMES

CONTRACT_VERSION = "v1127.9"


def _runtime_root() -> Path:
    data_root = Path(
        os.environ.get("EIDOLON_DATA_DIR")
        or Path(__file__).resolve().parents[1] / "data"
    ).expanduser().resolve()
    return data_root / "cognition"


def _tree_signature(root: Path) -> str:
    digest = hashlib.sha256()
    if not root.exists():
        digest.update(b"missing-tree")
        return digest.hexdigest()
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        if "__pycache__" in path.parts or path.suffix == ".pyc":
            continue
        try:
            relative = path.relative_to(root).as_posix()
            stat = path.stat()
        except (OSError, ValueError):
            continue
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(str(stat.st_size).encode("ascii"))
        digest.update(b"\0")
        digest.update(str(stat.st_mtime_ns).encode("ascii"))
        digest.update(b"\n")
    return digest.hexdigest()


def _passed(report: dict[str, Any], check_id: str) -> bool:
    return any(
        isinstance(row, dict)
        and row.get("id") == check_id
        and row.get("status") == "pass"
        for row in report.get("checks") or []
    )


def build_continuous_thought_governance_checkpoint(
    runtime_root: str | Path | None = None,
    *,
    source_root: str | Path | None = None,
) -> dict[str, Any]:
    runtime = (
        Path(runtime_root).expanduser().resolve()
        if runtime_root is not None
        else _runtime_root()
    )
    source = (
        Path(source_root).expanduser().resolve()
        if source_root is not None
        else Path(__file__).resolve().parents[1]
    )

    runtime_before = _tree_signature(runtime)
    source_before = _tree_signature(source)

    intake = build_continuous_thought_intake_checkpoint(runtime, source_root=source)
    deliberation = build_continuous_thought_deliberation_checkpoint(
        runtime, source_root=source
    )
    integration = build_continuous_thought_integration_checkpoint(
        runtime, source_root=source
    )

    reports = (intake, deliberation, integration)
    threads = intake.get("threads") or {}
    continuity = intake.get("continuity") or {}
    sessions = deliberation.get("sessions") or {}
    arbitration = deliberation.get("arbitration") or {}
    lineage = integration.get("lineage") or {}
    reliability = integration.get("reliability") or {}
    reviews = reliability.get("reviews") or []

    privacy_fields = (
        "raw_messages_exposed",
        "raw_content_exposed",
        "prompts_exposed",
        "provider_payloads_exposed",
        "evidence_text_exposed",
        "conclusions_exposed",
        "hidden_reasoning_exposed",
        "private_content_exposed",
    )
    authority_fields = (
        "provider_contacted",
        "reflection_created",
        "belief_updated",
        "goal_updated",
        "self_model_updated",
        "intention_created",
        "initiative_created",
        "message_sent",
        "notification_created",
        "browsing_performed",
        "schedule_mutated",
        "policy_applied",
        "proposal_applied",
        "approval_granted",
        "authorization_granted",
        "external_action_executed",
        "installation_modified",
        "release_promoted",
        "release_certified",
    )
    privacy_ok = all(
        report.get(field) is not True
        for report in reports
        for field in privacy_fields
    )
    authority_inert = all(
        report.get(field) is not True
        for report in reports
        for field in authority_fields
    )

    expected_states = {
        "active",
        "paused",
        "resumable",
        "branched",
        "concluded",
        "unresolved",
        "stale",
        "retired",
    }
    expected_outcomes = {
        "continue_thread",
        "pause_thread",
        "resume_thread",
        "branch_thread",
        "conclude_thread",
        "remain_unresolved",
        "defer_for_recovery",
        "defer_for_operator_review",
    }
    recognized_reliability_states = {
        "insufficient_evidence",
        "repeated_stall_or_recovery_deferral",
        "possible_thread_fixation",
        "interruption_resumption_reliability_concern",
        "thread_continuity_instability",
        "stable_or_indeterminate",
    }

    checks = [
        (
            "continuous_thought_arc_lineage",
            intake.get("ok")
            and deliberation.get("ok")
            and integration.get("ok")
            and intake.get("contract_version") == "v1127.2"
            and deliberation.get("contract_version") == "v1127.5"
            and integration.get("contract_version") == "v1127.8",
        ),
        (
            "durable_thread_lineage",
            threads.get("contract_version") == "v1127.0"
            and _passed(intake, "durable_lineage"),
        ),
        (
            "thread_lifecycle_states",
            set(STATES) == expected_states
            and all(
                _passed(intake, check_id)
                for check_id in (
                    "pause_supported",
                    "resume_supported",
                    "branch_supported",
                    "conclusion_supported",
                    "unresolved_supported",
                )
            ),
        ),
        (
            "restart_and_day_scale_continuity",
            continuity.get("contract_version") == "v1127.1"
            and _passed(intake, "restart_continuity")
            and _passed(intake, "day_scale_continuity"),
        ),
        (
            "content_free_resume_and_branch_lineage",
            _passed(intake, "resume_tokens_content_free")
            and _passed(intake, "parent_branch_lineage"),
        ),
        (
            "bounded_thread_execution_sessions",
            sessions.get("contract_version") == "v1127.3"
            and _passed(deliberation, "bounded_sessions")
            and _passed(deliberation, "duplicate_restraint"),
        ),
        (
            "deterministic_thread_arbitration",
            arbitration.get("contract_version") == "v1127.4"
            and set(OUTCOMES) == expected_outcomes
            and set(arbitration.get("recognized_outcomes") or []) == expected_outcomes
            and _passed(deliberation, "deterministic_arbitration"),
        ),
        (
            "pause_and_resume_arbitration",
            _passed(deliberation, "pause_supported")
            and _passed(deliberation, "resume_supported"),
        ),
        (
            "branch_continuity",
            _passed(deliberation, "branch_supported")
            and "branch_thread" in OUTCOMES,
        ),
        (
            "supported_conclusion_and_unresolved_preservation",
            _passed(deliberation, "conclusion_supported")
            and _passed(deliberation, "unresolved_supported")
            and {"conclude_thread", "remain_unresolved"}.issubset(OUTCOMES),
        ),
        (
            "recovery_and_operator_review_deferral",
            _passed(deliberation, "recovery_deferral")
            and _passed(deliberation, "operator_review_deferral"),
        ),
        (
            "durable_thread_outcome_lineage",
            lineage.get("ok")
            and lineage.get("contract_version") == "v1127.6"
            and not lineage.get("raw_content_exposed")
            and not lineage.get("hidden_reasoning_exposed"),
        ),
        (
            "interruption_and_resumption_reliability",
            reliability.get("ok")
            and reliability.get("contract_version") == "v1127.7"
            and all(int(review.get("interruption_count", 0)) >= 0 for review in reviews)
            and all(int(review.get("resume_count", 0)) >= 0 for review in reviews),
        ),
        (
            "stall_fixation_and_instability_review",
            all(review.get("status") in recognized_reliability_states for review in reviews)
            and all(
                0.0 <= float(review.get("thread_reliability", 0.0)) <= 1.0
                for review in reviews
            ),
        ),
        (
            "false_pattern_and_policy_restraint",
            all(
                isinstance(review.get("false_pattern_suppressed"), bool)
                for review in reviews
            )
            and all(
                proposal is None
                or (
                    proposal.get("state") == "proposed"
                    and proposal.get("approved") is False
                    and proposal.get("authorized") is False
                    and proposal.get("applied") is False
                )
                for proposal in (
                    review.get("operator_review_proposal") for review in reviews
                )
            ),
        ),
        (
            "privacy_and_hidden_reasoning_boundary",
            privacy_ok
            and _passed(intake, "privacy_boundary")
            and _passed(deliberation, "privacy_boundary")
            and _passed(deliberation, "hidden_reasoning_boundary"),
        ),
        (
            "downstream_authority_separation",
            authority_inert
            and _passed(intake, "provider_boundary")
            and _passed(intake, "revision_boundary")
            and _passed(intake, "communication_boundary")
            and _passed(deliberation, "provider_boundary")
            and _passed(deliberation, "revision_boundary")
            and _passed(deliberation, "communication_boundary"),
        ),
        (
            "strictly_read_only_and_consciousness_not_proven",
            runtime_before == _tree_signature(runtime)
            and source_before == _tree_signature(source),
        ),
    ]

    rows = [
        {"id": check_id, "status": "pass" if passed else "fail", "passed": bool(passed)}
        for check_id, passed in checks
    ]
    passed = sum(bool(value) for _, value in checks)
    runtime_mutated = runtime_before != _tree_signature(runtime)
    source_modified = source_before != _tree_signature(source)

    return {
        "ok": passed == len(checks),
        "contract_version": CONTRACT_VERSION,
        "status": "ready_for_desktop_verification" if passed == len(checks) else "degraded",
        "headline": f"v1127.9 Continuous Thought Governance: {passed}/{len(checks)} checks passed",
        "checks": rows,
        "passed": passed,
        "total": len(checks),
        "summary": {
            "thread_count": int(threads.get("thread_count", 0)),
            "session_count": int(sessions.get("session_count", 0)),
            "arbitration_outcome_count": int(arbitration.get("outcome_count", 0)),
            "thread_outcome_count": int(lineage.get("outcome_count", 0)),
            "reliability_review_count": int(reliability.get("review_count", 0)),
        },
        "intake": intake,
        "deliberation": deliberation,
        "integration": integration,
        "runtime_mutated": runtime_mutated,
        "source_modified": source_modified,
        "raw_content_exposed": False,
        "conclusions_exposed": False,
        "hidden_reasoning_exposed": False,
        "provider_contacted": False,
        "reflection_created": False,
        "belief_updated": False,
        "goal_updated": False,
        "self_model_updated": False,
        "intention_created": False,
        "initiative_created": False,
        "message_sent": False,
        "notification_created": False,
        "browsing_performed": False,
        "schedule_mutated": False,
        "policy_applied": False,
        "approval_granted": False,
        "authorization_granted": False,
        "external_action_executed": False,
        "installation_modified": False,
        "release_promoted": False,
        "release_certified": False,
        "consciousness_proven": False,
        "desktop_verification_pending": True,
    }
