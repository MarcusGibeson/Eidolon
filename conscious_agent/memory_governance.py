from __future__ import annotations

from release_metadata import RUNTIME_VERSION

from typing import Any

MEMORY_GOVERNANCE_VERSION = RUNTIME_VERSION
MEMORY_GOVERNANCE_BOUNDARY_SUMMARY = {
    "writes_memory": False,
    "alters_identity": False,
    "alters_personality": False,
    "rewrites_goals_or_purpose": False,
    "infers_approval_from_repeated_evidence": False,
    "infers_approval_from_operator_silence": False,
    "treats_lessons_as_stored_truth": False,
    "invokes_models_by_default": False,
    "executes_commands": False,
    "publishes_release_candidates": False,
    "continues_automatically": False,
    "requires_operator_memory_approval": True,
    "stages_candidates_only": True,
    "sensitive_identity_boundary_required": True,
    "contradiction_review_required": True,
}


def build_memory_candidate_intake_summary(source_type: str | None = None, evidence_items: list[str] | None = None) -> dict[str, Any]:
    """Build a review-only memory candidate intake summary."""
    items = evidence_items or []
    return {
        "version": MEMORY_GOVERNANCE_VERSION,
        "source_type": source_type or "operator_submitted_or_runtime_lesson_candidate",
        "evidence_item_count": len(items),
        "evidence_items": items,
        "candidate_state": "staged_for_operator_review_only",
        "writes_memory": False,
        "alters_identity": False,
        "message": "Memory candidates are intake records only; no memory or identity state is mutated.",
    }


def build_memory_candidate_classification_summary(candidate_type: str | None = None) -> dict[str, Any]:
    """Classify memory candidates without treating them as stored truth."""
    return {
        "version": MEMORY_GOVERNANCE_VERSION,
        "candidate_type": candidate_type or "unclassified_pending_operator_review",
        "supported_types": [
            "project_fact_candidate",
            "workflow_preference_candidate",
            "governance_rule_candidate",
            "capability_lesson_candidate",
            "sensitive_or_identity_boundary_candidate",
        ],
        "risk_score_scale": "0-100 advisory",
        "requires_sensitive_boundary_review": True,
        "treats_candidate_as_truth": False,
        "alters_identity": False,
    }


def build_memory_approval_packet_summary(candidate_id: str | None = None) -> dict[str, Any]:
    """Prepare an approval packet that separates proposed memory from stored memory."""
    return {
        "version": MEMORY_GOVERNANCE_VERSION,
        "candidate_id": candidate_id or "unbound_memory_candidate",
        "available_operator_decisions": ["approve", "reject", "defer", "request_revalidation"],
        "approval_state": "blocked_pending_explicit_operator_memory_approval",
        "writes_memory": False,
        "implies_approval": False,
        "expiration_or_revalidation_required": True,
        "message": "Approval packets describe candidate memory; they do not store it.",
    }


def build_memory_contradiction_review_summary(conflict_type: str | None = None) -> dict[str, Any]:
    """Review contradictions and staleness without correcting memory automatically."""
    return {
        "version": MEMORY_GOVERNANCE_VERSION,
        "conflict_type": conflict_type or "not_submitted",
        "review_axes": [
            "existing_rule_conflict",
            "project_state_conflict",
            "outdated_preference",
            "purpose_drift_conflict",
            "governance_boundary_conflict",
        ],
        "revalidation_recommended": True,
        "auto_correction_performed": False,
        "writes_memory": False,
        "rewrites_purpose": False,
    }


def render_memory_governance_lines(summary: dict[str, Any]) -> list[str]:
    lines: list[str] = []
    for key, value in summary.items():
        if isinstance(value, list):
            lines.append(f"- {key}: " + ", ".join(str(item) for item in value))
        else:
            lines.append(f"- {key}: {value}")
    return lines
