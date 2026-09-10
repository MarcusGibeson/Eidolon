from __future__ import annotations
"""Strictly read-only v1131.9 Read-Only Perception Governance checkpoint."""
import hashlib
import os
from pathlib import Path
from typing import Any
from read_only_perception_arbitration import OUTCOMES
from read_only_perception_deliberation_checkpoint import build_read_only_perception_deliberation_checkpoint
from read_only_perception_intake_checkpoint import build_read_only_perception_intake_checkpoint
from read_only_perception_integration_checkpoint import build_read_only_perception_integration_checkpoint
from read_only_perception_signals import CATEGORIES
CONTRACT_VERSION = "v1131.9"
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
def build_read_only_perception_governance_checkpoint(
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
    intake = build_read_only_perception_intake_checkpoint(runtime, source_root=source)
    deliberation = build_read_only_perception_deliberation_checkpoint(
        runtime, source_root=source
    )
    integration = build_read_only_perception_integration_checkpoint(
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
    outcome_counts = lineage.get("outcome_counts") or {}
    expected_categories = {
        "project_state",
        "system_event",
        "completed_work",
        "failure",
        "changed_file",
    }
    expected_outcomes = {
        "structural_review_eligible",
        "failure_review_prioritized",
        "changed_file_review_prioritized",
        "completed_work_review_eligible",
        "project_state_review_eligible",
        "system_event_review_eligible",
        "deliberate_no_perception",
        "defer_for_recovery",
        "defer_for_focus",
        "defer_for_cognitive_budget",
        "defer_for_conversation_sensitivity",
        "defer_for_operator_review",
        "await_prerequisite",
        "suppress_false_priority",
        "unresolved",
    }
    reliability_states = {
        "insufficient_evidence",
        "perception_continuity_failure",
        "stale_perception_pressure",
        "possible_over_perception",
        "possible_under_perception",
        "important_perception_missed",
        "perception_recommendation_instability",
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
        "raw_file_content_exposed",
        "raw_event_payload_exposed",
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
        "filesystem_modified",
    )
    privacy_ok = all(
        report.get(field) is not True
        for report in reports
        for field in privacy_fields
    ) and visible_status.get("raw_content_exposed") is not True and visible_status.get(
        "hidden_reasoning_exposed"
    ) is not True
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
            "read_only_perception_arc_lineage",
            intake.get("ok")
            and deliberation.get("ok")
            and integration.get("ok")
            and intake.get("contract_version") == "v1131.2"
            and deliberation.get("contract_version") == "v1131.5"
            and integration.get("contract_version") == "v1131.8",
        ),
        (
            "signal_categories_and_content_free_lineage",
            set(CATEGORIES) == expected_categories
            and all(row.get("signal_id") for row in recent_signals)
            and all(row.get("origin_ids") for row in recent_signals)
            and all(row.get("category") in expected_categories for row in recent_signals)
            and all(row.get("changed_path_digest") is not None for row in recent_signals)
            and _passed(intake, "category_coverage")
            and _passed(intake, "exact_lineage")
            and _passed(intake, "changed_files_content_free"),
        ),
        (
            "signal_project_and_recovery_constraints",
            all(row.get("project_id") is not None for row in recent_signals)
            and all(row.get("conversation_id") is not None for row in recent_signals)
            and all(row.get("cognitive_cost") is not None for row in recent_signals)
            and all(row.get("recovery_compatible") is not None for row in recent_signals)
            and _passed(intake, "project_and_conversation_continuity")
            and _passed(intake, "recovery_and_cost")
            and _passed(intake, "sensitivity_visible"),
        ),
        (
            "candidate_scope_overlap_and_lifecycle",
            all(row.get("signal_ids") for row in recent_candidates)
            and all(row.get("scope_digest") is not None for row in recent_candidates)
            and all(row.get("semantic_overlap_key") is not None for row in recent_candidates)
            and all(row.get("perception_purpose") is not None for row in recent_candidates)
            and _passed(intake, "scope_bounded")
            and _passed(intake, "overlap_visible"),
        ),
        (
            "bounded_content_free_deliberation_sessions",
            sessions.get("contract_version") == "v1131.3"
            and all(1 <= int(row.get("deliberation_budget") or 0) <= 6 for row in recent_sessions)
            and all(row.get("candidate_id") for row in recent_sessions)
            and all(row.get("signal_ids") is not None for row in recent_sessions)
            and _passed(deliberation, "bounded_sessions")
            and _passed(deliberation, "exact_candidate_lineage")
            and _passed(deliberation, "scope_preserved"),
        ),
        (
            "deterministic_recognized_arbitration",
            arbitration.get("contract_version") == "v1131.4"
            and set(OUTCOMES) == expected_outcomes
            and set(arbitration.get("recognized_outcomes") or []) == expected_outcomes
            and all(row.get("session_id") for row in recent_arbitrations),
        ),
        (
            "failure_change_and_structural_prioritization",
            {
                "failure_review_prioritized",
                "changed_file_review_prioritized",
                "completed_work_review_eligible",
                "project_state_review_eligible",
                "system_event_review_eligible",
                "structural_review_eligible",
            }.issubset(OUTCOMES)
            and _passed(deliberation, "failure_priority")
            and _passed(deliberation, "changed_file_priority"),
        ),
        (
            "deliberate_non_perception_and_deferral_restraint",
            {
                "deliberate_no_perception",
                "defer_for_recovery",
                "defer_for_focus",
                "defer_for_cognitive_budget",
                "defer_for_conversation_sensitivity",
                "defer_for_operator_review",
                "await_prerequisite",
                "suppress_false_priority",
                "unresolved",
            }.issubset(OUTCOMES)
            and _passed(deliberation, "deliberate_non_perception")
            and _passed(deliberation, "recovery_deferral")
            and _passed(deliberation, "focus_and_budget_deferral")
            and _passed(deliberation, "conversation_sensitivity")
            and _passed(deliberation, "operator_and_prerequisite_deferral")
            and _passed(deliberation, "false_priority_suppression"),
        ),
        (
            "durable_perception_outcome_lineage",
            lineage.get("ok")
            and lineage.get("contract_version") == "v1131.6"
            and all(row.get("perception_outcome_id") for row in recent_outcomes)
            and all(row.get("arbitration_id") for row in recent_outcomes)
            and all(row.get("session_id") for row in recent_outcomes)
            and all(row.get("candidate_id") for row in recent_outcomes)
            and _passed(integration, "outcome_lineage"),
        ),
        (
            "continuity_freshness_and_scope_preserved",
            all("continuity_state" in row for row in recent_outcomes)
            and all("restart_state" in row for row in recent_outcomes)
            and all("scope_digest" in row for row in recent_outcomes)
            and all("observation_freshness" in row for row in recent_outcomes)
            and _passed(integration, "perception_continuity")
            and _passed(integration, "scope_digest_preserved")
            and _passed(integration, "freshness_lineage"),
        ),
        (
            "reliability_review_catalog_and_false_pattern_restraint",
            reliability.get("ok")
            and reliability.get("contract_version") == "v1131.7"
            and all(review.get("status") in reliability_states for review in reviews)
            and all(isinstance(review.get("false_pattern_suppressed"), bool) for review in reviews)
            and _passed(integration, "pattern_review")
            and _passed(integration, "false_pattern_suppression"),
        ),
        (
            "failure_change_reliability_and_missed_detection",
            all("selected_count" in review for review in reviews)
            and all("continuity_failure_count" in review for review in reviews)
            and all("stale_observation_count" in review for review in reviews)
            and _passed(integration, "failure_change_reliability"),
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
                for proposal in (review.get("operator_review_proposal") for review in reviews)
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
            and _passed(deliberation, "read_only")
            and not integration.get("runtime_mutated")
            and not integration.get("source_modified"),
        ),
        (
            "no_raw_file_read_or_filesystem_mutation",
            not any(report.get("raw_file_content_exposed") for report in reports)
            and not any(report.get("filesystem_modified") for report in reports)
            and _passed(intake, "no_filesystem_mutation")
            and _passed(deliberation, "no_filesystem_mutation")
            and _passed(integration, "no_raw_read_or_mutation"),
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
    rows = [{"id": check_id, "status": "pass" if ok else "fail"} for check_id, ok in checks]
    passed = sum(bool(ok) for _, ok in checks)
    bounded_perception_count = sum(
        outcome_counts.get(key, 0)
        for key in (
            "structural_review_eligible",
            "failure_review_prioritized",
            "changed_file_review_prioritized",
            "completed_work_review_eligible",
            "project_state_review_eligible",
            "system_event_review_eligible",
        )
    )
    return {
        "ok": passed == len(checks),
        "contract_version": CONTRACT_VERSION,
        "status": "ready_for_desktop_verification" if passed == len(checks) else "degraded",
        "headline": f"v1131.9 Read-Only Perception Governance: {passed}/{len(checks)} checks passed",
        "checks": rows,
        "passed": passed,
        "total": len(checks),
        "summary": {
            "perception_signal_count": signals.get("signal_count", 0),
            "candidate_count": candidates.get("candidate_count", 0),
            "deliberation_session_count": sessions.get("session_count", 0),
            "arbitration_outcome_count": arbitration.get("outcome_count", 0),
            "perception_outcome_count": lineage.get("outcome_count", 0),
            "reliability_review_count": reliability.get("review_count", 0),
            "prioritized_failure_count": visible_status.get("prioritized_failure_count", 0),
            "prioritized_change_count": visible_status.get("prioritized_change_count", 0),
            "deliberate_no_perception_count": visible_status.get("deliberate_no_perception_count", 0),
        },
        "intake": intake,
        "deliberation": deliberation,
        "integration": integration,
        "runtime_mutated": runtime_mutated,
        "source_modified": source_modified,
        "raw_file_content_exposed": False,
        "raw_event_payload_exposed": False,
        "message_text_exposed": False,
        "prompt_exposed": False,
        "provider_payload_exposed": False,
        "raw_file_content_exposed": False,
        "raw_event_payload_exposed": False,
        "message_text_exposed": False,
        "prompt_exposed": False,
        "provider_payload_exposed": False,
        "message_text_exposed": False,
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
        "filesystem_modified": False,
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
        "perception_signal_created_by_checkpoint": False,
        "perception_signal_created_by_checkpoint": False,
        "perception_candidate_created_by_checkpoint": False,
        "deliberation_session_created_by_checkpoint": False,
        "arbitration_outcome_created_by_checkpoint": False,
        "perception_outcome_created_by_checkpoint": False,
        "desktop_verification": "pending",
        "desktop_verification_pending": True,
    }
