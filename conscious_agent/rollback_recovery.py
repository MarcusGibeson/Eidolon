from __future__ import annotations

from typing import Any

ROLLBACK_RECOVERY_VERSION = "1032.0"
ROLLBACK_RECOVERY_BOUNDARY_SUMMARY = {
    "runs_rollback": False,
    "edits_files": False,
    "executes_shell_commands": False,
    "infers_rollback_approval_from_failure": False,
    "infers_patch_approval_from_recovery_success": False,
    "mutates_memory": False,
    "alters_identity": False,
    "invokes_models_by_default": False,
    "publishes_release_candidates": False,
    "continues_automatically": False,
    "requires_operator_submitted_results": True,
    "requires_explicit_rollback_approval": True,
}


def build_rollback_scope_summary(packet_id: str | None = None, approved_files: list[str] | None = None) -> dict[str, Any]:
    """Build a review-only rollback scope binding summary."""
    files = approved_files or []
    return {
        "version": ROLLBACK_RECOVERY_VERSION,
        "packet_id": packet_id or "unbound_recovery_review_packet",
        "approved_file_count": len(files),
        "approved_files": files,
        "rollback_state": "blocked_pending_explicit_operator_rollback_approval",
        "runs_rollback": False,
        "edits_files": False,
        "message": "Rollback scope is bound for operator review only; no revert is executed.",
    }


def build_failure_damage_map_summary(failure_type: str | None = None) -> dict[str, Any]:
    """Classify possible failure categories without probing or changing the system."""
    kind = failure_type or "operator_result_not_submitted"
    affected_surfaces = [
        "source_files",
        "README_NEXT_STEPS.md",
        "README_RELEASE_HISTORY.md",
        "version_markers",
        "dashboard_routes",
        "api_routes",
        "cli_flags",
        "package_privacy",
        "smoke_verification",
    ]
    return {
        "version": ROLLBACK_RECOVERY_VERSION,
        "failure_type": kind,
        "affected_surfaces": affected_surfaces,
        "partial_application_detection_required": True,
        "diagnostic_overreach_allowed": False,
        "executes_shell_commands": False,
        "message": "Failure classification maps likely damage for review; it does not diagnose by running commands.",
    }


def build_recovery_checklist_summary() -> dict[str, Any]:
    """Prepare a manual operator recovery checklist without executing commands."""
    steps = [
        "stop further patch application work",
        "confirm exact failed application packet and approval receipt",
        "compare intended source edits against observed files",
        "review README_NEXT_STEPS.md and README_RELEASE_HISTORY.md drift",
        "review version marker and package privacy drift",
        "prepare manual file reverts from the approved rollback packet",
        "rerun operator-selected compile, fast smoke, install smoke, and package privacy checks",
        "record remaining drift for post-recovery review",
    ]
    return {
        "version": ROLLBACK_RECOVERY_VERSION,
        "steps": steps,
        "runs_commands": False,
        "runs_rollback": False,
        "requires_operator_execution": True,
    }


def build_post_recovery_review_summary(observed_status: str | None = None) -> dict[str, Any]:
    """Review recovery result intake without continuing into new work."""
    status = observed_status or "not_submitted"
    return {
        "version": ROLLBACK_RECOVERY_VERSION,
        "observed_status": status,
        "expected_clean_state_required": True,
        "remaining_drift_classifier": "pass_warn_block",
        "continues_automatically": False,
        "mutates_memory": False,
        "message": "Post-recovery review classifies submitted results and follow-up risk notes only.",
    }


def render_rollback_recovery_lines(summary: dict[str, Any]) -> list[str]:
    lines: list[str] = []
    for key, value in summary.items():
        if isinstance(value, list):
            lines.append(f"- {key}: " + ", ".join(str(item) for item in value))
        else:
            lines.append(f"- {key}: {value}")
    return lines
