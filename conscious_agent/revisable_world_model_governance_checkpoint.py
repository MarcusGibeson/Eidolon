from __future__ import annotations

"""Strictly read-only v1132.9 Revisable World Model Governance checkpoint."""

import hashlib
import os
from pathlib import Path
from typing import Any

from revisable_world_model_arbitration import OUTCOMES
from revisable_world_model_deliberation_checkpoint import build_revisable_world_model_deliberation_checkpoint
from revisable_world_model_intake_checkpoint import build_revisable_world_model_intake_checkpoint
from revisable_world_model_integration_checkpoint import build_revisable_world_model_integration_checkpoint
from revisable_world_model_signals import ENTITY_CATEGORIES, RELATION_CATEGORIES

CONTRACT_VERSION = "v1132.9"


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


def build_revisable_world_model_governance_checkpoint(
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

    intake = build_revisable_world_model_intake_checkpoint(runtime, source_root=source)
    deliberation = build_revisable_world_model_deliberation_checkpoint(
        runtime, source_root=source
    )
    integration = build_revisable_world_model_integration_checkpoint(
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

    expected_entities = {
        "person",
        "project",
        "event",
        "belief",
        "cause",
        "temporal_context",
    }
    expected_relations = {
        "associated_with",
        "involves",
        "precedes",
        "follows",
        "supports",
        "contradicts",
        "may_cause",
        "corrects",
        "contextualizes",
    }
    expected_outcomes = {
        "relationship_acceptance_recommended",
        "causal_relationship_review_recommended",
        "contradiction_reconciliation_recommended",
        "correction_acceptance_recommended",
        "temporal_relationship_review_recommended",
        "deliberate_non_acceptance",
        "defer_for_recovery",
        "defer_for_focus",
        "defer_for_cognitive_budget",
        "defer_for_operator_review",
        "await_prerequisite",
        "await_contradiction_review",
        "suppress_unsupported_causation",
        "suppress_false_certainty",
        "unresolved",
    }
    reliability_states = {
        "insufficient_evidence",
        "world_model_continuity_failure",
        "correction_instability",
        "possible_causal_overreach",
        "possible_under_acceptance",
        "world_model_recommendation_instability",
        "stable_or_indeterminate",
    }

    privacy_fields = (
        "raw_content_exposed",
        "evidence_text_exposed",
        "belief_text_exposed",
        "memory_text_exposed",
        "goal_text_exposed",
        "identity_text_exposed",
        "prompt_exposed",
        "provider_payload_exposed",
        "hidden_reasoning_exposed",
        "private_content_exposed",
    )
    authority_fields = (
        "browser_contacted",
        "browsing_performed",
        "provider_contacted",
        "model_contacted",
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
            "revisable_world_model_arc_lineage",
            intake.get("ok")
            and deliberation.get("ok")
            and integration.get("ok")
            and intake.get("contract_version") == "v1132.2"
            and deliberation.get("contract_version") == "v1132.5"
            and integration.get("contract_version") == "v1132.8",
        ),
        (
            "entity_and_relation_category_coverage",
            set(ENTITY_CATEGORIES) == expected_entities
            and set(RELATION_CATEGORIES) == expected_relations
            and _passed(intake, "entity_coverage")
            and _passed(intake, "relation_coverage"),
        ),
        (
            "exact_origin_evidence_and_predecessor_lineage",
            all(row.get("origin_ids") for row in recent_signals)
            and all(row.get("evidence_ids") for row in recent_signals)
            and all(row.get("predecessor_signal_ids") is not None for row in recent_signals)
            and _passed(intake, "exact_origin_lineage")
            and _passed(intake, "evidence_lineage")
            and _passed(intake, "predecessor_lineage"),
        ),
        (
            "temporal_uncertainty_and_correction_structure",
            all(row.get("temporal_context_id") is not None for row in recent_signals)
            and all(row.get("uncertainty") is not None for row in recent_signals)
            and all(row.get("correction") is not None for row in recent_candidates)
            and _passed(intake, "temporal_context")
            and _passed(intake, "uncertainty_visible")
            and _passed(intake, "correction_history"),
        ),
        (
            "candidate_scope_overlap_and_lifecycle",
            all(row.get("signal_ids") for row in recent_candidates)
            and all(row.get("scope_digest") is not None for row in recent_candidates)
            and all(row.get("semantic_overlap_key") is not None for row in recent_candidates)
            and _passed(intake, "candidate_states")
            and _passed(intake, "scope_bounded")
            and _passed(intake, "overlap_visible"),
        ),
        (
            "bounded_content_free_deliberation_sessions",
            sessions.get("contract_version") == "v1132.3"
            and all(1 <= int(row.get("deliberation_budget") or 0) <= 6 for row in recent_sessions)
            and all(row.get("candidate_id") for row in recent_sessions)
            and all(row.get("signal_ids") for row in recent_sessions)
            and _passed(deliberation, "bounded_sessions")
            and _passed(deliberation, "exact_candidate_lineage")
            and _passed(deliberation, "scope_preserved"),
        ),
        (
            "deterministic_recognized_arbitration",
            arbitration.get("contract_version") == "v1132.4"
            and set(OUTCOMES) == expected_outcomes
            and set(arbitration.get("recognized_outcomes") or []) == expected_outcomes
            and all(row.get("session_id") for row in recent_arbitrations),
        ),
        (
            "supported_acceptance_and_review_paths",
            {
                "relationship_acceptance_recommended",
                "causal_relationship_review_recommended",
                "contradiction_reconciliation_recommended",
                "correction_acceptance_recommended",
                "temporal_relationship_review_recommended",
            }.issubset(OUTCOMES)
            and _passed(deliberation, "acceptance_recommendation")
            and _passed(deliberation, "causal_review")
            and _passed(deliberation, "contradiction_reconciliation")
            and _passed(deliberation, "correction_acceptance")
            and _passed(deliberation, "temporal_review"),
        ),
        (
            "deliberate_non_acceptance_and_bounded_deferral",
            {
                "deliberate_non_acceptance",
                "defer_for_recovery",
                "defer_for_focus",
                "defer_for_cognitive_budget",
                "defer_for_operator_review",
                "await_prerequisite",
                "await_contradiction_review",
            }.issubset(OUTCOMES)
            and _passed(deliberation, "deliberate_non_acceptance")
            and _passed(deliberation, "recovery_focus_budget_deferral")
            and _passed(deliberation, "operator_prerequisite_contradiction_deferral"),
        ),
        (
            "unsupported_causation_and_false_certainty_suppression",
            {
                "suppress_unsupported_causation",
                "suppress_false_certainty",
            }.issubset(OUTCOMES)
            and _passed(deliberation, "unsupported_causation_suppression")
            and _passed(deliberation, "false_certainty_suppression"),
        ),
        (
            "durable_world_model_outcome_lineage",
            lineage.get("ok")
            and lineage.get("contract_version") == "v1132.6"
            and all(row.get("world_model_outcome_id") for row in recent_outcomes)
            and all(row.get("arbitration_id") for row in recent_outcomes)
            and all(row.get("candidate_id") for row in recent_outcomes)
            and _passed(integration, "outcome_lineage")
            and _passed(integration, "exact_arbitration_lineage"),
        ),
        (
            "scope_temporal_correction_and_continuity_lineage",
            all("scope_digest" in row for row in recent_outcomes)
            and all("continuity_state" in row for row in recent_outcomes)
            and all("temporal_state" in row for row in recent_outcomes)
            and all("correction_state" in row for row in recent_outcomes)
            and _passed(integration, "scope_digest_preserved")
            and _passed(integration, "continuity_state")
            and _passed(integration, "temporal_state")
            and _passed(integration, "correction_state"),
        ),
        (
            "reliability_and_false_pattern_restraint",
            reliability.get("ok")
            and reliability.get("contract_version") == "v1132.7"
            and all(review.get("status") in reliability_states for review in reviews)
            and all(isinstance(review.get("false_pattern_suppressed"), bool) for review in reviews)
            and _passed(integration, "reliability_review")
            and _passed(integration, "false_pattern_suppression"),
        ),
        (
            "correction_stability_and_causal_overreach_review",
            all("correction_count" in review for review in reviews)
            and all("reversal_count" in review for review in reviews)
            and all("continuity_failure_count" in review for review in reviews)
            and _passed(integration, "correction_stability_review"),
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
            "strict_downstream_authority_and_revision_separation",
            authority_inert
            and structural_boundaries_inert
            and _passed(intake, "authority_separation")
            and _passed(deliberation, "authority_separation")
            and _passed(integration, "no_autonomous_revision")
            and _passed(integration, "authority_separation"),
        ),
        (
            "strictly_read_only_desktop_pending_no_consciousness_claim",
            not any(report.get("runtime_mutated") for report in reports)
            and not any(report.get("source_modified") for report in reports)
            and all(report.get("desktop_verification") == "pending" for report in reports)
            and not any(report.get("consciousness_proven") is True for report in reports),
        ),
    ]

    runtime_after = _tree_signature(runtime)
    source_after = _tree_signature(source)
    runtime_mutated = runtime_before != runtime_after
    source_modified = source_before != source_after
    rows = [{"id": check_id, "status": "pass" if ok else "fail"} for check_id, ok in checks]
    passed = sum(bool(ok) for _, ok in checks)
    accepted_count = sum(
        outcome_counts.get(key, 0)
        for key in (
            "relationship_acceptance_recommended",
            "causal_relationship_review_recommended",
            "contradiction_reconciliation_recommended",
            "correction_acceptance_recommended",
            "temporal_relationship_review_recommended",
        )
    )

    return {
        "ok": passed == len(checks),
        "contract_version": CONTRACT_VERSION,
        "status": "ready_for_desktop_verification" if passed == len(checks) else "degraded",
        "headline": f"v1132.9 Revisable World Model Governance: {passed}/{len(checks)} checks passed",
        "checks": rows,
        "passed": passed,
        "total": len(checks),
        "summary": {
            "world_model_signal_count": signals.get("signal_count", 0),
            "candidate_count": candidates.get("candidate_count", 0),
            "deliberation_session_count": sessions.get("session_count", 0),
            "arbitration_outcome_count": arbitration.get("outcome_count", 0),
            "world_model_outcome_count": lineage.get("outcome_count", 0),
            "reliability_review_count": reliability.get("review_count", 0),
            "accepted_or_review_recommended_count": accepted_count,
            "deliberate_non_acceptance_count": outcome_counts.get("deliberate_non_acceptance", 0),
        },
        "intake": intake,
        "deliberation": deliberation,
        "integration": integration,
        "runtime_mutated": runtime_mutated,
        "source_modified": source_modified,
        "raw_content_exposed": False,
        "evidence_text_exposed": False,
        "belief_text_exposed": False,
        "memory_text_exposed": False,
        "goal_text_exposed": False,
        "identity_text_exposed": False,
        "prompt_exposed": False,
        "provider_payload_exposed": False,
        "hidden_reasoning_exposed": False,
        "browser_contacted": False,
        "browsing_performed": False,
        "provider_contacted": False,
        "model_contacted": False,
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
        "filesystem_modified": False,
        "consciousness_proven": False,
        "world_model_signal_created_by_checkpoint": False,
        "world_model_candidate_created_by_checkpoint": False,
        "deliberation_session_created_by_checkpoint": False,
        "arbitration_outcome_created_by_checkpoint": False,
        "world_model_outcome_created_by_checkpoint": False,
        "world_model_revision_applied_by_checkpoint": False,
        "desktop_verification": "pending",
        "desktop_verification_pending": True,
    }
