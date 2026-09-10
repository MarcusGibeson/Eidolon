from __future__ import annotations

"""Strictly read-only v1124.9 Selected Attention and Reflective Focus Governance checkpoint."""

import hashlib
import os
from pathlib import Path
from typing import Any

from reflective_focus_continuity_review_checkpoint import build_reflective_focus_continuity_review_checkpoint
from reflective_focus_deliberation_checkpoint import build_reflective_focus_deliberation_checkpoint
from selected_attention_focus_intake_checkpoint import build_selected_attention_focus_intake_checkpoint

CONTRACT_VERSION = "v1124.9"


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


def build_selected_attention_reflective_focus_governance_checkpoint(
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

    intake = build_selected_attention_focus_intake_checkpoint(
        runtime, source_root=source
    )
    deliberation = build_reflective_focus_deliberation_checkpoint(
        runtime, source_root=source
    )
    continuity = build_reflective_focus_continuity_review_checkpoint(
        runtime, source_root=source
    )

    runtime_mutated = runtime_before != _tree_signature(runtime)
    source_modified = source_before != _tree_signature(source)
    reports = (intake, deliberation, continuity)

    privacy_fields = (
        "raw_messages_exposed",
        "raw_content_exposed",
        "prompts_exposed",
        "provider_payloads_exposed",
        "evidence_text_exposed",
        "motivational_text_exposed",
        "identity_text_exposed",
        "objective_text_exposed",
        "hidden_reasoning_exposed",
        "private_content_exposed",
    )
    downstream_authority_fields = (
        "reflection_created",
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
    downstream_authority_inert = all(
        report.get(field) is not True
        for report in reports
        for field in downstream_authority_fields
    )

    checks = [
        (
            "selected_attention_reflective_focus_arc_lineage",
            intake.get("ok")
            and deliberation.get("ok")
            and continuity.get("ok")
            and intake.get("contract_version") == "v1124.2"
            and deliberation.get("contract_version") == "v1124.5"
            and continuity.get("contract_version") == "v1124.8",
        ),
        (
            "selected_attention_eligibility_lineage",
            _passed(intake, "selected_attention_lineage")
            and _passed(intake, "eligible_outcome_boundary"),
        ),
        (
            "selection_support_and_recovery_gates",
            _passed(intake, "importance_relevance_uncertainty_gate")
            and _passed(intake, "operator_review_boundary")
            and _passed(intake, "recovery_compatibility_gate"),
        ),
        (
            "selection_duplicate_and_lifecycle_restraint",
            _passed(intake, "duplicate_selection_suppression")
            and _passed(intake, "attention_lifecycle_history"),
        ),
        (
            "reflective_focus_state_lineage",
            _passed(intake, "focus_state_lineage")
            and _passed(intake, "bounded_focus_budget")
            and _passed(intake, "interruptibility_preserved")
            and _passed(intake, "recovery_compatible_focus")
            and _passed(intake, "restart_continuity"),
        ),
        (
            "content_free_intake_privacy",
            _passed(intake, "content_free_privacy") and privacy_ok,
        ),
        (
            "bounded_reflective_focus_sessions",
            _passed(deliberation, "bounded_focus_sessions")
            and _passed(deliberation, "duplicate_session_suppression"),
        ),
        (
            "deterministic_focus_arbitration",
            _passed(deliberation, "deterministic_focus_arbitration")
            and _passed(deliberation, "continuation_requires_support"),
        ),
        (
            "deliberate_disengagement_and_recovery_suspension",
            _passed(deliberation, "deliberate_disengagement")
            and _passed(deliberation, "recovery_aware_suspension")
            and _passed(deliberation, "operator_review_deferral"),
        ),
        (
            "overlap_uncertainty_and_budget_restraint",
            _passed(deliberation, "overlap_resolution")
            and _passed(deliberation, "uncertainty_restraint")
            and _passed(deliberation, "focus_budget_preserved")
            and _passed(deliberation, "interruptibility_preserved"),
        ),
        (
            "durable_focus_outcome_lineage",
            _passed(continuity, "outcome_lineage")
            and _passed(continuity, "history_preserved")
            and _passed(continuity, "supersession_without_deletion"),
        ),
        (
            "interruption_resumption_continuity",
            _passed(continuity, "interruption_resumption_continuity"),
        ),
        (
            "repeated_disengagement_and_recovery_review",
            _passed(continuity, "repeated_disengagement_review")
            and _passed(continuity, "recovery_suspension_review"),
        ),
        (
            "fixation_and_false_pattern_restraint",
            _passed(continuity, "fixation_review")
            and _passed(continuity, "false_pattern_suppression"),
        ),
        (
            "focus_reliability_evidence",
            _passed(continuity, "focus_reliability_evidence"),
        ),
        (
            "operator_reviewed_policy_boundary",
            _passed(continuity, "operator_reviewed_policy_proposals")
            and _passed(continuity, "policy_not_applied"),
        ),
        (
            "selected_attention_downstream_authority_separation",
            downstream_authority_inert
            and _passed(intake, "reflection_separation")
            and _passed(intake, "intention_initiative_separation")
            and _passed(deliberation, "reflection_separation")
            and _passed(deliberation, "intention_initiative_separation")
            and _passed(continuity, "reflection_not_created")
            and _passed(continuity, "initiative_not_created")
            and _passed(continuity, "authority_separation"),
        ),
        (
            "source_runtime_and_desktop_boundary",
            not _inside(runtime, source)
            and not runtime_mutated
            and not source_modified
            and intake.get("desktop_verification_pending") is True
            and deliberation.get("desktop_verification_pending") is True
            and continuity.get("desktop_verification") == "pending",
        ),
    ]

    rows = [
        {"id": name, "status": "pass" if passed else "blocked"}
        for name, passed in checks
    ]
    ready = all(passed for _, passed in checks)

    intake_summary = intake.get("summary") or {}
    deliberation_summary = deliberation.get("summary") or {}
    continuity_summary = continuity.get("summary") or {}

    return {
        "ok": ready,
        "status": (
            "ready_for_desktop_verification"
            if ready
            else "pending_desktop_verification"
        ),
        "contract_version": CONTRACT_VERSION,
        "headline": (
            "Selected attention and reflective focus governance preserves eligibility-gated "
            "internal focus, bounded deterministic deliberation, deliberate disengagement, "
            "durable continuity, reliability restraint, and operator-reviewed policy boundaries "
            "without creating reflection or granting downstream authority."
        ),
        "epistemic_status": "candidate_artificial_consciousness_not_proven",
        "consciousness_claimed": False,
        "checks": rows,
        "check_count": len(rows),
        "summary": {
            "attention_count": intake_summary.get("attention_count", 0),
            "focus_count": intake_summary.get("focus_count", 0),
            "session_count": deliberation_summary.get("session_count", 0),
            "outcome_count": continuity_summary.get("outcome_count", 0),
            "reviewed_attention_count": continuity_summary.get(
                "reviewed_attention_count", 0
            ),
            "selected_attention_focus_intake": intake_summary,
            "reflective_focus_deliberation": deliberation_summary,
            "reflective_focus_continuity_review": continuity_summary,
        },
        "runtime_external": not _inside(runtime, source),
        "runtime_mutated": runtime_mutated,
        "source_modified": source_modified,
        "selected_attention_created_by_checkpoint": False,
        "reflective_focus_created_by_checkpoint": False,
        "raw_messages_exposed": False,
        "raw_content_exposed": False,
        "prompts_exposed": False,
        "provider_payloads_exposed": False,
        "evidence_text_exposed": False,
        "motivational_text_exposed": False,
        "identity_text_exposed": False,
        "objective_text_exposed": False,
        "hidden_reasoning_exposed": False,
        "private_content_exposed": False,
        "reflection_created": False,
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
        "selected_attention_focus_intake": intake,
        "reflective_focus_deliberation": deliberation,
        "reflective_focus_continuity_review": continuity,
    }
