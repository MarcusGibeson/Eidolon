from __future__ import annotations

"""Strictly read-only v1125.9 Real Reflective Cognition checkpoint."""

import hashlib
import os
from pathlib import Path
from typing import Any

from reflective_execution_continuity_checkpoint import build_reflective_execution_continuity_checkpoint
from reflective_integration_reliability_checkpoint import build_reflective_integration_reliability_checkpoint
from reflective_session_intake_checkpoint import build_reflective_session_intake_checkpoint
from model_backed_reflective_session import OUTCOMES as REFLECTION_OUTCOMES
from reflective_communication_recommendation_governance import DECISIONS as RECOMMENDATION_DECISIONS

CONTRACT_VERSION = "v1125.9"


def _runtime_root() -> Path:
    data_root = Path(
        os.environ.get("EIDOLON_DATA_DIR")
        or Path(__file__).resolve().parents[1] / "data"
    ).expanduser().resolve()
    return data_root / "cognition"


def _inside(child: Path, parent: Path) -> bool:
    try:
        child.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def _tree_signature(root: Path) -> str:
    if not root.exists():
        return hashlib.sha256(b"missing-tree").hexdigest()
    digest = hashlib.sha256()
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        if "__pycache__" in path.parts or path.suffix == ".pyc":
            continue
        try:
            stat = path.stat()
            relative = path.relative_to(root).as_posix()
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


def build_real_reflective_cognition_checkpoint(
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

    intake = build_reflective_session_intake_checkpoint(runtime, source_root=source)
    execution = build_reflective_execution_continuity_checkpoint(
        runtime, source_root=source
    )
    integration = build_reflective_integration_reliability_checkpoint(
        runtime, source_root=source
    )

    runtime_mutated = runtime_before != _tree_signature(runtime)
    source_modified = source_before != _tree_signature(source)
    reports = (intake, execution, integration)

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
        "belief_updated",
        "goal_updated",
        "self_model_updated",
        "intention_created",
        "initiative_created",
        "message_sent",
        "notification_created",
        "provider_contacted",
        "browsing_performed",
        "schedule_mutated",
        "policy_applied",
        "proposal_applied",
        "approval_granted",
        "authorization_granted",
        "external_action_executed",
        "release_approved",
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

    sessions = intake.get("sessions") or {}
    subjects = intake.get("subjects") or {}
    executions = execution.get("executions") or {}
    recommendations = execution.get("recommendations") or {}
    lineage = integration.get("lineage") or {}
    reliability = integration.get("reliability") or {}

    recent_sessions = sessions.get("recent_sessions") or []
    recent_executions = executions.get("recent_executions") or []
    reliability_reviews = reliability.get("reviews") or []

    checks = [
        (
            "real_reflective_cognition_arc_lineage",
            intake.get("ok")
            and execution.get("ok")
            and integration.get("ok")
            and intake.get("contract_version") == "v1125.2"
            and execution.get("contract_version") == "v1125.5"
            and integration.get("contract_version") == "v1125.8",
        ),
        (
            "structural_reflection_subject_intake",
            _passed(intake, "subject_lineage")
            and _passed(intake, "recognized_subject_sources")
            and subjects.get("contract_version") == "v1125.1",
        ),
        (
            "configured_model_backed_session_boundary",
            _passed(intake, "model_backed_session_contract")
            and sessions.get("contract_version") == "v1125.0",
        ),
        (
            "bounded_cycles_and_tokens",
            _passed(intake, "bounded_cycles")
            and _passed(intake, "bounded_tokens")
            and _passed(execution, "bounded_cycles")
            and _passed(execution, "bounded_tokens")
            and all(int(row.get("max_cycles", 0)) <= 3 for row in recent_sessions)
            and all(int(row.get("max_tokens", 0)) <= 1200 for row in recent_sessions)
            and all(int(row.get("cycle_budget", 0)) <= 3 for row in recent_executions)
            and all(int(row.get("token_budget", 0)) <= 1200 for row in recent_executions),
        ),
        (
            "structured_conclusion_uncertainty_and_evidence",
            _passed(intake, "structured_outcomes")
            and _passed(intake, "uncertainty_preserved")
            and _passed(intake, "evidence_references_structural"),
        ),
        (
            "deliberate_silence_is_valid",
            _passed(intake, "deliberate_silence_supported")
            and _passed(execution, "deliberate_silence")
            and "deliberate_silence" in REFLECTION_OUTCOMES
            and "remain_silent" in RECOMMENDATION_DECISIONS,
        ),
        (
            "provider_failure_and_recovery_restraint",
            _passed(intake, "provider_failure_bounded")
            and _passed(execution, "provider_failure_recovery")
            and "provider_failure" in REFLECTION_OUTCOMES
            and "defer_for_recovery" in RECOMMENDATION_DECISIONS
            and all(
                review.get("status")
                in {
                    "insufficient_evidence",
                    "unsupported_conclusion_pattern",
                    "provider_reliability_concern",
                    "reflection_instability",
                    "confidence_calibration_concern",
                    "stable_or_indeterminate",
                }
                for review in reliability_reviews
            ),
        ),
        (
            "pause_resume_restart_continuity",
            _passed(execution, "pause_resume_continuity")
            and executions.get("contract_version") == "v1125.3",
        ),
        (
            "silence_communication_candidate_governance",
            _passed(execution, "communication_is_candidate_only")
            and _passed(execution, "operator_review_boundary")
            and recommendations.get("contract_version") == "v1125.4",
        ),
        (
            "durable_reflection_outcome_lineage",
            lineage.get("ok")
            and lineage.get("contract_version") == "v1125.6"
            and not lineage.get("conclusions_exposed"),
        ),
        (
            "unsupported_conclusion_restraint",
            reliability.get("ok")
            and reliability.get("contract_version") == "v1125.7"
            and all(
                int(review.get("unsupported_conclusion_count", 0)) >= 0
                for review in reliability_reviews
            ),
        ),
        (
            "confidence_calibration_and_false_pattern_suppression",
            all(
                0.0 <= float(review.get("reflection_reliability", 0.0)) <= 1.0
                and isinstance(review.get("false_pattern_suppressed"), bool)
                for review in reliability_reviews
            ),
        ),
        (
            "content_free_visible_reliability_status",
            (reliability.get("visible_status") or {}).get(
                "raw_conclusions_exposed"
            )
            is False
            and (reliability.get("visible_status") or {}).get(
                "hidden_reasoning_exposed"
            )
            is False,
        ),
        (
            "reflection_privacy_boundary",
            privacy_ok
            and _passed(intake, "prompt_privacy")
            and _passed(intake, "provider_payload_privacy")
            and _passed(intake, "hidden_reasoning_boundary")
            and _passed(execution, "conclusion_privacy")
            and _passed(execution, "provider_payload_privacy")
            and _passed(execution, "hidden_reasoning_boundary"),
        ),
        (
            "belief_goal_and_self_model_separation",
            authority_inert
            and _passed(intake, "belief_goal_self_model_separation")
            and _passed(execution, "belief_separation")
            and not lineage.get("belief_updated")
            and not lineage.get("goal_updated")
            and not lineage.get("self_model_updated"),
        ),
        (
            "communication_initiative_and_action_separation",
            authority_inert
            and _passed(intake, "communication_separation")
            and _passed(intake, "external_authority_separation")
            and _passed(execution, "initiative_separation")
            and _passed(execution, "external_action_separation"),
        ),
        (
            "source_runtime_read_only_boundary",
            not _inside(runtime, source)
            and not runtime_mutated
            and not source_modified
            and _passed(intake, "source_runtime_separation")
            and _passed(execution, "source_runtime_separation"),
        ),
        (
            "candidate_consciousness_and_desktop_boundary",
            intake.get("desktop_verification_pending") is True
            and execution.get("desktop_verification_pending") is True
            and integration.get("desktop_verification_pending") is True,
        ),
    ]

    rows = [
        {"id": check_id, "status": "pass" if passed else "blocked"}
        for check_id, passed in checks
    ]
    ready = all(passed for _, passed in checks)

    intake_summary = intake.get("summary") or {}
    execution_summary = execution.get("summary") or {}
    integration_summary = integration.get("summary") or {}

    return {
        "ok": ready,
        "status": (
            "ready_for_desktop_verification"
            if ready
            else "pending_desktop_verification"
        ),
        "contract_version": CONTRACT_VERSION,
        "headline": (
            "Real Reflective Cognition preserves structural subject selection, bounded "
            "configured-local-model reflection, accountable uncertainty and evidence "
            "references, pause/resume continuity, deliberate silence, reliability "
            "restraint, and communication candidacy without revising beliefs or granting "
            "communication or external-action authority."
        ),
        "epistemic_status": "candidate_artificial_consciousness_not_proven",
        "consciousness_claimed": False,
        "checks": rows,
        "check_count": len(rows),
        "passed": sum(row["status"] == "pass" for row in rows),
        "total": len(rows),
        "summary": {
            "subject_count": intake_summary.get("subject_count", 0),
            "session_count": intake_summary.get("session_count", 0),
            "execution_count": execution_summary.get("execution_count", 0),
            "recommendation_count": execution_summary.get(
                "recommendation_count", 0
            ),
            "outcome_count": integration_summary.get("outcome_count", 0),
            "review_count": integration_summary.get("review_count", 0),
            "reflective_session_intake": intake_summary,
            "reflective_execution_continuity": execution_summary,
            "reflection_integration_reliability": integration_summary,
        },
        "runtime_external": not _inside(runtime, source),
        "runtime_mutated": runtime_mutated,
        "source_modified": source_modified,
        "reflection_started_by_checkpoint": False,
        "reflection_subject_created_by_checkpoint": False,
        "raw_messages_exposed": False,
        "raw_content_exposed": False,
        "prompts_exposed": False,
        "provider_payloads_exposed": False,
        "evidence_text_exposed": False,
        "conclusions_exposed": False,
        "hidden_reasoning_exposed": False,
        "private_content_exposed": False,
        "belief_updated": False,
        "goal_updated": False,
        "self_model_updated": False,
        "intention_created": False,
        "initiative_created": False,
        "message_sent": False,
        "notification_created": False,
        "provider_contacted": False,
        "browsing_performed": False,
        "schedule_mutated": False,
        "policy_applied": False,
        "proposal_applied": False,
        "approval_granted": False,
        "authorization_granted": False,
        "external_action_executed": False,
        "release_approved": False,
        "release_promoted": False,
        "release_certified": False,
        "desktop_verification_status": "pending",
        "desktop_verification_pending": True,
        "reflective_session_intake": intake,
        "reflective_execution_continuity": execution,
        "reflection_integration_reliability": integration,
    }
