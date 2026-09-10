from __future__ import annotations

"""Strictly read-only v1126.9 Reflection Quality Governance checkpoint."""

import hashlib
import os
from pathlib import Path
from typing import Any

from reflection_quality_deliberation_checkpoint import build_reflection_quality_deliberation_checkpoint
from reflection_quality_intake_checkpoint import build_reflection_quality_intake_checkpoint
from reflection_quality_integration_checkpoint import build_reflection_quality_integration_checkpoint
from reflection_quality_signals import CATEGORIES
from reflection_quality_evaluation_candidates import STATES
from reflection_quality_arbitration import OUTCOMES

CONTRACT_VERSION = "v1126.9"


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


def build_reflection_quality_governance_checkpoint(
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

    intake = build_reflection_quality_intake_checkpoint(runtime, source_root=source)
    deliberation = build_reflection_quality_deliberation_checkpoint(
        runtime, source_root=source
    )
    integration = build_reflection_quality_integration_checkpoint(
        runtime, source_root=source
    )

    runtime_mutated = runtime_before != _tree_signature(runtime)
    source_modified = source_before != _tree_signature(source)
    reports = (intake, deliberation, integration)

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

    signals = intake.get("signals") or {}
    candidates = intake.get("candidates") or {}
    sessions = deliberation.get("sessions") or {}
    arbitration = deliberation.get("arbitration") or {}
    lineage = integration.get("lineage") or {}
    reliability = integration.get("reliability") or {}
    visible_status = reliability.get("visible_status") or {}
    reviews = reliability.get("reviews") or []

    checks = [
        (
            "reflection_quality_arc_lineage",
            intake.get("ok")
            and deliberation.get("ok")
            and integration.get("ok")
            and intake.get("contract_version") == "v1126.2"
            and deliberation.get("contract_version") == "v1126.5"
            and integration.get("contract_version") == "v1126.8",
        ),
        (
            "distinct_quality_categories",
            signals.get("contract_version") == "v1126.0"
            and {
                "unsupported_conclusion",
                "contradiction",
                "confidence_mismatch",
                "provider_failure",
                "provider_recovery",
                "well_supported",
            }.issubset(CATEGORIES)
            and _passed(intake, "unsupported_conclusion_separated")
            and _passed(intake, "contradiction_separated")
            and _passed(intake, "confidence_mismatch_separated")
            and _passed(intake, "provider_failure_recovery_separated"),
        ),
        (
            "quality_signal_lineage_and_content_restraint",
            _passed(intake, "structural_lineage_preserved")
            and _passed(intake, "conclusions_not_exposed")
            and signals.get("conclusions_exposed") is False,
        ),
        (
            "evaluation_candidate_lifecycle_and_restraint",
            candidates.get("contract_version") == "v1126.1"
            and set(candidates.get("recognized_states") or []) == set(STATES)
            and _passed(intake, "recognized_candidate_states")
            and _passed(intake, "recovery_and_load_restraint"),
        ),
        (
            "bounded_quality_evaluation_sessions",
            sessions.get("contract_version") == "v1126.3"
            and _passed(deliberation, "bounded_quality_sessions")
            and _passed(deliberation, "duplicate_session_restraint"),
        ),
        (
            "deterministic_quality_arbitration",
            arbitration.get("contract_version") == "v1126.4"
            and set(arbitration.get("recognized_outcomes") or []) == set(OUTCOMES)
            and _passed(deliberation, "deterministic_quality_arbitration")
            and _passed(deliberation, "recognized_outcomes"),
        ),
        (
            "unsupported_conclusion_and_contradiction_handling",
            _passed(deliberation, "unsupported_resolution")
            and _passed(deliberation, "contradiction_handling")
            and {"mark_unsupported", "reconcile_contradiction"}.issubset(OUTCOMES),
        ),
        (
            "confidence_and_provider_recovery_governance",
            _passed(deliberation, "confidence_calibration")
            and _passed(deliberation, "provider_recovery_continuity")
            and _passed(deliberation, "operator_review_deferral")
            and {
                "recalibrate_confidence",
                "defer_for_provider_recovery",
                "defer_for_operator_review",
            }.issubset(OUTCOMES),
        ),
        (
            "supported_retention_and_unresolved_preservation",
            _passed(deliberation, "deliberate_retention")
            and _passed(deliberation, "unresolved_preserved")
            and {"retain_supported_conclusion", "unresolved"}.issubset(OUTCOMES),
        ),
        (
            "durable_quality_outcome_lineage",
            lineage.get("ok")
            and lineage.get("contract_version") == "v1126.6"
            and not lineage.get("conclusions_exposed")
            and not lineage.get("evidence_text_exposed"),
        ),
        (
            "quality_reliability_review",
            reliability.get("ok")
            and reliability.get("contract_version") == "v1126.7"
            and all(int(review.get("sample_size", 0)) >= 0 for review in reviews)
            and all(0.0 <= float(review.get("quality_reliability", 0.0)) <= 1.0 for review in reviews),
        ),
        (
            "repeated_failure_and_uncertainty_patterns",
            all(
                review.get("status")
                in {
                    "insufficient_evidence",
                    "repeated_unsupported_conclusion",
                    "provider_recovery_reliability_concern",
                    "quality_evaluation_instability",
                    "persistent_quality_uncertainty",
                    "stable_or_indeterminate",
                }
                for review in reviews
            ),
        ),
        (
            "false_pattern_and_policy_restraint",
            all(isinstance(review.get("false_pattern_suppressed"), bool) for review in reviews)
            and all(
                proposal is None
                or (
                    proposal.get("state") == "proposed"
                    and proposal.get("approved") is False
                    and proposal.get("authorized") is False
                    and proposal.get("applied") is False
                )
                for proposal in (review.get("operator_review_proposal") for review in reviews)
            ),
        ),
        (
            "content_free_visible_quality_status",
            visible_status.get("raw_conclusions_exposed") is False
            and visible_status.get("evidence_text_exposed") is False
            and visible_status.get("hidden_reasoning_exposed") is False,
        ),
        (
            "quality_privacy_boundary",
            privacy_ok
            and _passed(intake, "hidden_reasoning_not_exposed")
            and _passed(deliberation, "conclusions_not_exposed")
            and _passed(deliberation, "hidden_reasoning_not_exposed"),
        ),
        (
            "revision_provider_communication_and_action_separation",
            authority_inert
            and _passed(intake, "no_internal_revision")
            and _passed(intake, "no_provider_contact")
            and _passed(intake, "no_message_or_action")
            and _passed(deliberation, "no_internal_revision")
            and _passed(deliberation, "no_provider_or_communication_authority")
            and _passed(deliberation, "no_execution_authority"),
        ),
        (
            "source_runtime_read_only_boundary",
            not _inside(runtime, source)
            and not runtime_mutated
            and not source_modified
            and _passed(intake, "runtime_read_only")
            and _passed(intake, "source_read_only")
            and _passed(deliberation, "source_runtime_read_only"),
        ),
        (
            "candidate_consciousness_and_desktop_boundary",
            deliberation.get("desktop_verification_pending") is True
            and integration.get("desktop_verification_pending") is True,
        ),
    ]

    rows = [
        {"id": check_id, "status": "pass" if passed else "blocked"}
        for check_id, passed in checks
    ]
    ready = all(passed for _, passed in checks)

    return {
        "ok": ready,
        "status": "ready_for_desktop_verification" if ready else "pending_desktop_verification",
        "contract_version": CONTRACT_VERSION,
        "headline": (
            "Reflection Quality Governance preserves distinct quality signals, bounded "
            "evaluation, accountable outcome lineage, contradiction and unsupported-"
            "conclusion restraint, confidence calibration, provider-recovery continuity, "
            "and false-pattern suppression without revising internal records or granting "
            "provider, communication, approval, authorization, or execution authority."
        ),
        "epistemic_status": "candidate_artificial_consciousness_not_proven",
        "consciousness_claimed": False,
        "checks": rows,
        "check_count": len(rows),
        "passed": sum(row["status"] == "pass" for row in rows),
        "total": len(rows),
        "summary": {
            "signal_count": signals.get("signal_count", 0),
            "candidate_count": candidates.get("candidate_count", 0),
            "session_count": sessions.get("session_count", 0),
            "arbitration_outcome_count": arbitration.get("outcome_count", 0),
            "quality_outcome_count": lineage.get("outcome_count", 0),
            "quality_review_count": reliability.get("review_count", 0),
        },
        "runtime_external": not _inside(runtime, source),
        "runtime_mutated": runtime_mutated,
        "source_modified": source_modified,
        "quality_signal_created_by_checkpoint": False,
        "quality_candidate_created_by_checkpoint": False,
        "quality_session_created_by_checkpoint": False,
        "quality_outcome_created_by_checkpoint": False,
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
        "reflection_quality_intake": intake,
        "reflection_quality_deliberation": deliberation,
        "reflection_quality_integration_reliability": integration,
    }
