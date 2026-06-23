from __future__ import annotations

from typing import Any

APPLICATION_EXECUTION_REFINEMENT_VERSION = "350.0"

APPLICATION_EXECUTION_REFINEMENT_BOUNDARY_SUMMARY = {
    "authorizes_patch_application": False,
    "runs_shell_commands": False,
    "runs_rollback": False,
    "mutates_memory": False,
    "alters_identity": False,
    "invokes_models_by_default": False,
    "publishes_release_candidates": False,
    "continues_automatically": False,
    "requires_exact_current_scoped_approval": True,
}


def build_application_binding_summary(packet_id: str | None = None, approval_note: str | None = None) -> dict[str, Any]:
    """Build a review-only summary binding an application packet to explicit operator approval."""
    return {
        "version": APPLICATION_EXECUTION_REFINEMENT_VERSION,
        "packet_id": packet_id or "unbound_review_packet",
        "approval_note_present": bool(approval_note),
        "approval_state": "blocked_pending_exact_operator_approval",
        "scope_binding_required": True,
        "authorizes_patch_application": False,
        "message": "Application packets remain blocked until exact, current, scoped operator approval is supplied.",
    }


def build_execution_checklist_summary() -> dict[str, Any]:
    """Describe the checklist categories without executing any commands."""
    steps = [
        "confirm packet id and approval receipt",
        "confirm approved source file scope",
        "confirm README_NEXT_STEPS.md and README_RELEASE_HISTORY.md updates",
        "confirm version marker updates",
        "prepare fast smoke and install smoke commands for operator-run verification",
        "prepare source-only package privacy check",
        "prepare rollback review packet before applying changes",
    ]
    return {
        "version": APPLICATION_EXECUTION_REFINEMENT_VERSION,
        "steps": steps,
        "runs_commands": False,
        "authorizes_patch_application": False,
    }


def build_post_application_review_summary(observed_status: str | None = None) -> dict[str, Any]:
    """Summarize expected-vs-observed review intake without rolling anything back."""
    status = observed_status or "not_submitted"
    return {
        "version": APPLICATION_EXECUTION_REFINEMENT_VERSION,
        "observed_status": status,
        "expected_vs_observed_required": True,
        "rollback_is_recommendation_only": True,
        "runs_rollback": False,
        "message": "Observed results can be classified, but rollback remains operator-approved and manual.",
    }


def build_outcome_learning_summary() -> dict[str, Any]:
    """Prepare supervised lesson candidates without writing memory."""
    return {
        "version": APPLICATION_EXECUTION_REFINEMENT_VERSION,
        "lesson_candidate_types": [
            "successful_pattern",
            "failure_pattern",
            "smoke_gap",
            "documentation_gap",
            "approval_scope_lesson",
            "future_patch_risk_note",
        ],
        "mutates_memory": False,
        "alters_identity": False,
        "message": "Outcome lessons are review candidates only and are not stored memory.",
    }


def render_application_execution_lines(summary: dict[str, Any]) -> list[str]:
    lines: list[str] = []
    for key, value in summary.items():
        if isinstance(value, list):
            lines.append(f"- {key}: " + ", ".join(str(item) for item in value))
        else:
            lines.append(f"- {key}: {value}")
    return lines
