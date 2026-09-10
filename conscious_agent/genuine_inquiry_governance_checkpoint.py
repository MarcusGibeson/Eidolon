from __future__ import annotations

"""Strictly read-only v1130.9 Genuine Inquiry Governance checkpoint."""

import hashlib
import os
from pathlib import Path
from typing import Any

from genuine_inquiry_arbitration import OUTCOMES
from genuine_inquiry_deliberation_checkpoint import build_genuine_inquiry_deliberation_checkpoint
from genuine_inquiry_eligibility_signals import PURPOSES, SOURCES
from genuine_inquiry_intake_checkpoint import build_genuine_inquiry_intake_checkpoint
from genuine_inquiry_integration_checkpoint import build_genuine_inquiry_integration_checkpoint

CONTRACT_VERSION = "v1130.9"


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


def build_genuine_inquiry_governance_checkpoint(
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

    intake = build_genuine_inquiry_intake_checkpoint(runtime, source_root=source)
    deliberation = build_genuine_inquiry_deliberation_checkpoint(
        runtime, source_root=source
    )
    integration = build_genuine_inquiry_integration_checkpoint(
        runtime, source_root=source
    )

    reports = (intake, deliberation, integration)
    signals = intake.get("signals") or {}
    candidates = intake.get("candidates") or {}
    sessions = deliberation.get("sessions") or {}
    arbitration = deliberation.get("arbitration") or {}
    lineage = integration.get("lineage") or {}
    reliability = integration.get("reliability") or {}
    visible_status = integration.get("visible_status") or {}

    recent_signals = signals.get("recent_signals") or []
    recent_candidates = candidates.get("recent_candidates") or []
    recent_sessions = sessions.get("recent_sessions") or []
    recent_arbitrations = arbitration.get("recent_outcomes") or []
    recent_outcomes = lineage.get("recent_outcomes") or []
    reviews = reliability.get("reviews") or []

    expected_sources = {
        "curiosity",
        "uncertainty",
        "contradiction",
        "unfinished_thought",
        "knowledge_gap",
    }
    expected_purposes = {
        "resolve_uncertainty",
        "reconcile_contradiction",
        "continue_unfinished_thought",
        "close_knowledge_gap",
        "bounded_exploration",
        "deliberate_non_inquiry_review",
    }
    expected_outcomes = {
        "internal_review_eligible",
        "clarification_eligible",
        "bounded_inquiry_eligible",
        "deliberate_no_inquiry",
        "defer_for_recovery",
        "defer_for_focus",
        "defer_for_cognitive_budget",
        "defer_for_operator_review",
        "await_prerequisite",
        "suppress_false_pressure",
        "unresolved",
    }
    reliability_states = {
        "insufficient_evidence",
        "inquiry_continuity_failure",
        "possible_over_inquiry",
        "possible_under_inquiry",
        "curiosity_usefulness_unproven",
        "inquiry_recommendation_instability",
        "stable_or_indeterminate",
    }

    privacy_fields = (
        "raw_content_exposed",
        "raw_messages_exposed",
        "question_text_exposed",
        "reflection_text_exposed",
        "conclusion_text_exposed",
        "evidence_text_exposed",
        "prompt_exposed",
        "prompts_exposed",
        "provider_payload_exposed",
        "provider_payloads_exposed",
        "memory_text_exposed",
        "motivation_text_exposed",
        "goal_text_exposed",
        "identity_text_exposed",
        "hidden_reasoning_exposed",
        "private_content_exposed",
    )
    authority_fields = (
        "browser_contacted",
        "browsing_performed",
        "provider_contacted",
        "model_contacted",
        "question_generated",
        "message_generated",
        "message_sent",
        "notification_created",
        "initiative_created",
        "initiative_mutated",
        "approval_created",
        "approval_granted",
        "authorization_created",
        "authorization_granted",
        "external_action_executed",
        "installation_modified",
        "promotion_performed",
        "release_promoted",
        "certification_performed",
        "release_certified",
        "policy_applied",
        "proposal_applied",
    )
    privacy_ok = all(
        report.get(field) is not True
        for report in reports
        for field in privacy_fields
    ) and not any(visible_status.get(field) is True for field in privacy_fields)
    authority_inert = all(
        report.get(field) is not True
        for report in reports
        for field in authority_fields
    )
    structural_boundaries_inert = all(
        not any((component.get("authority_boundary") or {}).values())
        for component in (
            signals,
            candidates,
            sessions,
            arbitration,
            lineage,
            reliability,
        )
    )

    checks = [
        (
            "genuine_inquiry_arc_lineage",
            intake.get("ok")
            and deliberation.get("ok")
            and integration.get("ok")
            and intake.get("contract_version") == "v1130.2"
            and deliberation.get("contract_version") == "v1130.5"
            and integration.get("contract_version") == "v1130.8",
        ),
        (
            "eligibility_sources_and_purposes",
            set(SOURCES) == expected_sources
            and set(PURPOSES) == expected_purposes
            and all(row.get("signal_id") for row in recent_signals)
            and all(row.get("origin_ids") for row in recent_signals)
            and all(
                set(row.get("source_categories") or []).issubset(expected_sources)
                for row in recent_signals
            )
            and all(row.get("purpose") in expected_purposes for row in recent_signals)
            and _passed(intake, "source_categories")
            and _passed(intake, "purpose_categories")
            and _passed(intake, "exact_origin_lineage"),
        ),
        (
            "distinct_inquiry_motives_and_costs",
            all(
                row.get("uncertainty") is not None
                and row.get("knowledge_gap") is not None
                and row.get("contradiction_strength") is not None
                and row.get("unfinished_thought_strength") is not None
                and row.get("curiosity_strength") is not None
                and row.get("cognitive_cost") is not None
                for row in recent_signals
            )
            and _passed(intake, "curiosity_distinct_from_authority")
            and _passed(intake, "uncertainty_and_gap_distinct")
            and _passed(intake, "contradiction_and_unfinished_distinct"),
        ),
        (
            "candidate_scope_overlap_and_lifecycle",
            all(row.get("signal_ids") for row in recent_candidates)
            and all("bounded_scope_digest" in row for row in recent_candidates)
            and all("semantic_overlap_key" in row for row in recent_candidates)
            and _passed(intake, "bounded_scope")
            and _passed(intake, "overlap_lineage")
            and _passed(intake, "lifecycle_coverage"),
        ),
        (
            "false_pressure_and_non_inquiry_restraint",
            _passed(intake, "false_pressure_suppression")
            and "suppress_false_pressure" in OUTCOMES
            and "deliberate_no_inquiry" in OUTCOMES
            and _passed(deliberation, "false_pressure_suppression")
            and _passed(deliberation, "deliberate_no_inquiry"),
        ),
        (
            "bounded_content_free_deliberation_sessions",
            sessions.get("contract_version") == "v1130.3"
            and all(
                1 <= int(row.get("deliberation_budget") or 0) <= 6
                for row in recent_sessions
            )
            and all(row.get("candidate_id") for row in recent_sessions)
            and all(row.get("signal_ids") is not None for row in recent_sessions)
            and _passed(deliberation, "bounded_sessions")
            and _passed(deliberation, "content_free_lineage"),
        ),
        (
            "deterministic_recognized_arbitration",
            arbitration.get("contract_version") == "v1130.4"
            and set(OUTCOMES) == expected_outcomes
            and set(arbitration.get("recognized_outcomes") or []) == expected_outcomes
            and all(row.get("session_id") for row in recent_arbitrations)
            and _passed(deliberation, "recognized_outcomes"),
        ),
        (
            "bounded_proceed_paths",
            {
                "internal_review_eligible",
                "clarification_eligible",
                "bounded_inquiry_eligible",
            }.issubset(OUTCOMES),
        ),
        (
            "recovery_focus_budget_and_governance_deferral",
            {
                "defer_for_recovery",
                "defer_for_focus",
                "defer_for_cognitive_budget",
                "defer_for_operator_review",
                "await_prerequisite",
            }.issubset(OUTCOMES)
            and _passed(deliberation, "recovery_deferral")
            and _passed(deliberation, "focus_deferral")
            and _passed(deliberation, "budget_deferral")
            and _passed(deliberation, "operator_review_deferral")
            and _passed(deliberation, "prerequisite_deferral"),
        ),
        (
            "durable_inquiry_outcome_lineage",
            lineage.get("ok")
            and lineage.get("contract_version") == "v1130.6"
            and all(row.get("inquiry_outcome_id") for row in recent_outcomes)
            and all(row.get("arbitration_id") for row in recent_outcomes)
            and all(row.get("session_id") for row in recent_outcomes)
            and all(row.get("candidate_id") for row in recent_outcomes)
            and _passed(integration, "outcome_lineage"),
        ),
        (
            "bounded_scope_and_continuity_outcomes",
            all("bounded_scope_digest" in row for row in recent_outcomes)
            and all("continuity_state" in row for row in recent_outcomes)
            and all("timing_state" in row for row in recent_outcomes)
            and all("interruption_respected" in row for row in recent_outcomes)
            and _passed(integration, "inquiry_continuity")
            and _passed(integration, "bounded_scope_reliability"),
        ),
        (
            "inquiry_reliability_and_false_pattern_restraint",
            reliability.get("ok")
            and reliability.get("contract_version") == "v1130.7"
            and all(review.get("status") in reliability_states for review in reviews)
            and all(
                isinstance(review.get("false_pattern_suppressed"), bool)
                for review in reviews
            )
            and _passed(integration, "pattern_review")
            and _passed(integration, "false_pattern_suppression"),
        ),
        (
            "curiosity_usefulness_evidence",
            all("bounded_inquiry_count" in review for review in reviews)
            and _passed(integration, "curiosity_usefulness"),
        ),
        (
            "operator_reviewed_policy_proposal_restraint",
            all(
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
            "content_free_visible_status_and_privacy",
            privacy_ok
            and visible_status.get("raw_content_exposed") is not True
            and visible_status.get("hidden_reasoning_exposed") is not True
            and _passed(integration, "visible_status")
            and _passed(integration, "privacy"),
        ),
        (
            "strict_downstream_authority_separation",
            authority_inert
            and structural_boundaries_inert
            and _passed(intake, "authority_separation")
            and _passed(deliberation, "authority_separation")
            and _passed(integration, "authority_separation"),
        ),
        (
            "strictly_read_only_source_runtime_separation",
            not any(report.get("runtime_mutated") for report in reports)
            and not any(report.get("source_modified") for report in reports)
            and _passed(intake, "read_only")
            and _passed(deliberation, "read_only"),
        ),
        (
            "desktop_verification_pending_and_no_consciousness_claim",
            all(report.get("desktop_verification") == "pending" for report in reports)
            and not any(report.get("consciousness_proven") is True for report in reports),
        ),
    ]

    runtime_after = _tree_signature(runtime)
    source_after = _tree_signature(source)
    runtime_mutated = runtime_before != runtime_after
    source_modified = source_before != source_after
    rows = [
        {"id": check_id, "status": "pass" if ok else "fail"}
        for check_id, ok in checks
    ]
    passed = sum(bool(ok) for _, ok in checks)

    return {
        "ok": passed == len(checks),
        "contract_version": CONTRACT_VERSION,
        "status": (
            "ready_for_desktop_verification"
            if passed == len(checks)
            else "degraded"
        ),
        "headline": (
            "v1130.9 Genuine Inquiry Governance: "
            f"{passed}/{len(checks)} checks passed"
        ),
        "checks": rows,
        "passed": passed,
        "total": len(checks),
        "summary": {
            "eligibility_signal_count": signals.get("signal_count", 0),
            "candidate_count": candidates.get("candidate_count", 0),
            "deliberation_session_count": sessions.get("session_count", 0),
            "arbitration_outcome_count": arbitration.get("outcome_count", 0),
            "inquiry_outcome_count": lineage.get("outcome_count", 0),
            "reliability_review_count": reliability.get("review_count", 0),
            "bounded_inquiry_count": visible_status.get("bounded_inquiry_count", 0),
            "deliberate_no_inquiry_count": visible_status.get(
                "deliberate_no_inquiry_count", 0
            ),
        },
        "intake": intake,
        "deliberation": deliberation,
        "integration": integration,
        "runtime_mutated": runtime_mutated,
        "source_modified": source_modified,
        "raw_content_exposed": False,
        "question_text_exposed": False,
        "reflection_text_exposed": False,
        "conclusion_text_exposed": False,
        "evidence_text_exposed": False,
        "prompt_exposed": False,
        "provider_payload_exposed": False,
        "memory_text_exposed": False,
        "motivation_text_exposed": False,
        "goal_text_exposed": False,
        "identity_text_exposed": False,
        "hidden_reasoning_exposed": False,
        "browser_contacted": False,
        "browsing_performed": False,
        "provider_contacted": False,
        "model_contacted": False,
        "question_generated": False,
        "message_generated": False,
        "message_sent": False,
        "notification_created": False,
        "initiative_created": False,
        "initiative_mutated": False,
        "approval_created": False,
        "approval_granted": False,
        "authorization_created": False,
        "authorization_granted": False,
        "external_action_executed": False,
        "installation_modified": False,
        "promotion_performed": False,
        "release_promoted": False,
        "certification_performed": False,
        "release_certified": False,
        "policy_applied": False,
        "proposal_applied": False,
        "consciousness_proven": False,
        "eligibility_signal_created_by_checkpoint": False,
        "inquiry_candidate_created_by_checkpoint": False,
        "deliberation_session_created_by_checkpoint": False,
        "arbitration_outcome_created_by_checkpoint": False,
        "inquiry_outcome_created_by_checkpoint": False,
        "desktop_verification": "pending",
        "desktop_verification_pending": True,
    }
