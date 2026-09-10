from __future__ import annotations

"""Strictly read-only v1128.9 Reflection-Supported Revision Governance checkpoint."""

import hashlib
import os
from pathlib import Path
from typing import Any

from reflection_supported_revision_arbitration import OUTCOMES
from reflection_supported_revision_deliberation_checkpoint import build_reflection_supported_revision_deliberation_checkpoint
from reflection_supported_revision_intake_checkpoint import build_reflection_supported_revision_intake_checkpoint
from reflection_supported_revision_integration_checkpoint import build_reflection_supported_revision_integration_checkpoint
from reflection_supported_revision_signals import TARGET_TYPES

CONTRACT_VERSION = "v1128.9"


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
            payload = path.read_bytes()
        except (OSError, ValueError):
            continue
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(payload)
        digest.update(b"\n")
    return digest.hexdigest()


def _passed(report: dict[str, Any], check_id: str) -> bool:
    return any(
        isinstance(row, dict)
        and (row.get("id") == check_id or row.get("check") == check_id)
        and row.get("status") == "pass"
        for row in report.get("checks") or []
    )


def build_reflection_supported_revision_governance_checkpoint(
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

    intake = build_reflection_supported_revision_intake_checkpoint(
        runtime, source_root=source
    )
    deliberation = build_reflection_supported_revision_deliberation_checkpoint(
        runtime, source_root=source
    )
    integration = build_reflection_supported_revision_integration_checkpoint(
        runtime, source_root=source
    )

    reports = (intake, deliberation, integration)
    signals = intake.get("signals") or {}
    candidates = intake.get("candidates") or {}
    sessions = deliberation.get("sessions") or {}
    arbitration = deliberation.get("arbitration") or {}
    lineage = integration.get("lineage") or {}
    reliability = integration.get("reliability") or {}
    reviews = reliability.get("reviews") or []
    recent_signals = signals.get("recent_signals") or []
    recent_candidates = candidates.get("recent_candidates") or []
    recent_outcomes = lineage.get("recent_outcomes") or []

    privacy_fields = (
        "raw_messages_exposed",
        "raw_content_exposed",
        "prompts_exposed",
        "provider_payloads_exposed",
        "evidence_text_exposed",
        "conclusion_text_exposed",
        "hidden_reasoning_exposed",
        "private_content_exposed",
    )
    authority_fields = (
        "belief_revised",
        "motivation_revised",
        "goal_revised",
        "self_model_revised",
        "revision_applied",
        "target_revised",
        "provider_contacted",
        "reflection_created",
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

    expected_outcomes = {
        "recommend_belief_revision",
        "recommend_motivation_revision",
        "recommend_goal_revision",
        "recommend_self_model_revision",
        "deliberate_non_application",
        "defer_for_recovery",
        "defer_for_operator_review",
        "await_prerequisite",
        "unresolved",
    }
    recognized_reliability_states = {
        "insufficient_evidence",
        "repeated_correction_pattern",
        "persistent_revision_uncertainty",
        "revision_recommendation_instability",
        "possible_revision_pressure",
        "stable_or_indeterminate",
    }

    checks = [
        (
            "revision_governance_arc_lineage",
            intake.get("ok")
            and deliberation.get("ok")
            and integration.get("ok")
            and intake.get("contract_version") == "v1128.2"
            and deliberation.get("contract_version") == "v1128.5"
            and integration.get("contract_version") == "v1128.8",
        ),
        (
            "revision_target_domains",
            set(TARGET_TYPES) == {"belief", "motivation", "goal", "self_model"}
            and _passed(intake, "target_domains"),
        ),
        (
            "reflection_quality_and_evidence_lineage",
            all(row.get("reflection_outcome_id") for row in recent_signals)
            and all(row.get("quality_outcome_id") for row in recent_signals)
            and all(isinstance(row.get("evidence_refs"), list) for row in recent_signals)
            and _passed(intake, "reflection_lineage")
            and _passed(intake, "quality_lineage"),
        ),
        (
            "uncertainty_correction_and_candidate_lineage",
            all(row.get("uncertainty") is not None for row in recent_signals)
            and all(row.get("correction_required") is not None for row in recent_signals)
            and all(row.get("signal_ids") for row in recent_candidates)
            and _passed(intake, "candidate_lineage"),
        ),
        (
            "prerequisite_recovery_and_operator_gates",
            all(isinstance(row.get("prerequisite_ids"), list) for row in recent_candidates)
            and all(row.get("recovery_compatible") is not None for row in recent_candidates)
            and all(row.get("operator_review_required") is not None for row in recent_candidates)
            and _passed(intake, "prerequisite_handling")
            and _passed(intake, "recovery_compatibility")
            and _passed(intake, "operator_review_boundary"),
        ),
        (
            "bounded_revision_deliberation_sessions",
            sessions.get("contract_version") == "v1128.3"
            and _passed(deliberation, "bounded_revision_sessions"),
        ),
        (
            "deterministic_revision_arbitration",
            arbitration.get("contract_version") == "v1128.4"
            and set(OUTCOMES) == expected_outcomes
            and set(arbitration.get("recognized_outcomes") or []) == expected_outcomes
            and _passed(deliberation, "deterministic_target_arbitration"),
        ),
        (
            "target_specific_revision_recommendations",
            {
                "recommend_belief_revision",
                "recommend_motivation_revision",
                "recommend_goal_revision",
                "recommend_self_model_revision",
            }.issubset(OUTCOMES),
        ),
        (
            "deliberate_non_application_and_unresolved_preservation",
            {"deliberate_non_application", "unresolved"}.issubset(OUTCOMES)
            and _passed(deliberation, "deliberate_non_application")
            and _passed(deliberation, "unresolved_preserved"),
        ),
        (
            "recovery_operator_and_prerequisite_deferral",
            {
                "defer_for_recovery",
                "defer_for_operator_review",
                "await_prerequisite",
            }.issubset(OUTCOMES)
            and _passed(deliberation, "recovery_deferral")
            and _passed(deliberation, "operator_review_deferral")
            and _passed(deliberation, "prerequisite_deferral"),
        ),
        (
            "durable_revision_outcome_lineage",
            lineage.get("ok")
            and lineage.get("contract_version") == "v1128.6"
            and all(row.get("arbitration_id") for row in recent_outcomes)
            and all(row.get("target_type") in TARGET_TYPES for row in recent_outcomes),
        ),
        (
            "predecessor_and_correction_history",
            all("predecessor_revision_outcome_id" in row for row in recent_outcomes)
            and all("correction_of_revision_outcome_id" in row for row in recent_outcomes)
            and all(isinstance(row.get("history"), list) for row in recent_outcomes),
        ),
        (
            "revision_integration_reliability",
            reliability.get("ok")
            and reliability.get("contract_version") == "v1128.7"
            and all(review.get("status") in recognized_reliability_states for review in reviews)
            and all(
                0.0 <= float(review.get("revision_reliability", 0.0)) <= 1.0
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
                for proposal in (
                    review.get("operator_review_proposal") for review in reviews
                )
            ),
        ),
        (
            "privacy_and_hidden_reasoning_boundary",
            privacy_ok
            and _passed(intake, "privacy_boundary")
            and _passed(deliberation, "content_not_exposed")
            and _passed(deliberation, "hidden_reasoning_not_exposed"),
        ),
        (
            "no_revision_application_or_target_mutation",
            authority_inert
            and _passed(intake, "no_target_revision")
            and _passed(deliberation, "no_target_revision")
            and _passed(deliberation, "no_application_or_execution"),
        ),
        (
            "downstream_authority_separation",
            authority_inert
            and _passed(intake, "no_provider_contact")
            and _passed(intake, "no_communication")
            and _passed(intake, "no_execution_authority"),
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
        "headline": f"v1128.9 Reflection-Supported Revision Governance: {passed}/{len(checks)} checks passed",
        "checks": rows,
        "passed": passed,
        "total": len(checks),
        "summary": {
            "signal_count": signals.get("signal_count", 0),
            "candidate_count": candidates.get("candidate_count", 0),
            "session_count": sessions.get("session_count", 0),
            "arbitration_outcome_count": arbitration.get("outcome_count", 0),
            "revision_outcome_count": lineage.get("outcome_count", 0),
            "reliability_review_count": reliability.get("review_count", 0),
        },
        "intake": intake,
        "deliberation": deliberation,
        "integration": integration,
        "runtime_mutated": runtime_mutated,
        "source_modified": source_modified,
        "raw_content_exposed": False,
        "conclusion_text_exposed": False,
        "evidence_text_exposed": False,
        "hidden_reasoning_exposed": False,
        "belief_revised": False,
        "motivation_revised": False,
        "goal_revised": False,
        "self_model_revised": False,
        "revision_applied": False,
        "target_revised": False,
        "provider_contacted": False,
        "reflection_created": False,
        "message_sent": False,
        "notification_created": False,
        "initiative_created": False,
        "approval_granted": False,
        "authorization_granted": False,
        "external_action_executed": False,
        "installation_modified": False,
        "release_promoted": False,
        "release_certified": False,
        "consciousness_proven": False,
        "revision_signal_created_by_checkpoint": False,
        "revision_candidate_created_by_checkpoint": False,
        "revision_session_created_by_checkpoint": False,
        "revision_outcome_created_by_checkpoint": False,
        "desktop_verification_pending": True,
    }
