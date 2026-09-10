from __future__ import annotations

"""Strictly read-only v1123.9 Reflective Attention and Salience Governance checkpoint."""

import hashlib
import os
from pathlib import Path
from typing import Any

from reflective_attention_continuity_review_checkpoint import build_reflective_attention_continuity_review_checkpoint
from reflective_attention_deliberation_checkpoint import build_reflective_attention_deliberation_checkpoint
from reflective_attention_salience_intake_checkpoint import build_reflective_attention_salience_intake_checkpoint

CONTRACT_VERSION = "v1123.9"


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


def build_reflective_attention_salience_governance_checkpoint(
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

    intake = build_reflective_attention_salience_intake_checkpoint(
        runtime, source_root=source
    )
    deliberation = build_reflective_attention_deliberation_checkpoint(
        runtime, source_root=source
    )
    continuity = build_reflective_attention_continuity_review_checkpoint(
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
    authority_fields = (
        "attention_selected",
        "reflection_created",
        "intention_created",
        "initiative_created",
        "message_sent",
        "notification_created",
        "provider_contacted",
        "browsing_performed",
        "schedule_mutated",
        "policy_applied",
        "proposal_created",
        "proposal_applied",
        "approval_granted",
        "authorization_granted",
        "external_action_executed",
        "release_approved",
        "release_promoted",
        "release_certified",
    )
    privacy_ok = all(report.get(field) is not True for report in reports for field in privacy_fields)
    authority_inert = all(report.get(field) is not True for report in reports for field in authority_fields)

    checks = [
        (
            "reflective_attention_arc_lineage",
            intake.get("ok")
            and deliberation.get("ok")
            and continuity.get("ok")
            and intake.get("contract_version") == "v1123.2"
            and deliberation.get("contract_version") == "v1123.5"
            and continuity.get("contract_version") == "v1123.8",
        ),
        (
            "salience_signal_candidate_lineage",
            _passed(intake, "salience_signal_persistence_lineage")
            and _passed(intake, "attention_review_candidate_persistence_lineage"),
        ),
        (
            "durable_salience_novelty_separation",
            _passed(intake, "durable_salience_transient_novelty_separation"),
        ),
        (
            "importance_urgency_uncertainty_sensitivity_separation",
            _passed(intake, "importance_urgency_separation")
            and _passed(intake, "uncertainty_sensitivity_separation"),
        ),
        (
            "duplicate_overlap_and_false_urgency_restraint",
            _passed(intake, "duplicate_suppression")
            and _passed(intake, "semantic_overlap_handling")
            and _passed(intake, "false_urgency_novelty_restraint"),
        ),
        (
            "cognitive_load_recovery_and_lifecycle_continuity",
            _passed(intake, "cognitive_load_recovery_interaction")
            and _passed(
                intake,
                "correction_retraction_supersession_staleness_retirement",
            )
            and _passed(intake, "restart_project_provider_switch_continuity"),
        ),
        (
            "bounded_attention_review_sessions",
            _passed(deliberation, "session_lineage")
            and _passed(deliberation, "bounded_review_sessions"),
        ),
        (
            "deterministic_salience_comparison",
            _passed(deliberation, "arbitration_lineage")
            and _passed(deliberation, "deterministic_salience_comparison"),
        ),
        (
            "conflict_overlap_and_unresolved_preservation",
            _passed(deliberation, "conflict_overlap_handling")
            and _passed(deliberation, "unresolved_preserved"),
        ),
        (
            "deliberate_non_selection_and_recovery_deferral",
            _passed(deliberation, "deliberate_non_selection")
            and _passed(deliberation, "recovery_aware_deferral"),
        ),
        (
            "durable_attention_outcome_lineage",
            _passed(continuity, "outcome_lineage")
            and _passed(continuity, "history_preserved")
            and _passed(continuity, "supersession_without_deletion"),
        ),
        (
            "interruption_resumption_continuity",
            _passed(continuity, "interruption_resumption_continuity"),
        ),
        (
            "distraction_fixation_and_false_pattern_review",
            _passed(continuity, "repeated_distraction_review")
            and _passed(continuity, "fixation_review")
            and _passed(continuity, "false_pattern_suppression"),
        ),
        (
            "attention_reliability_evidence",
            _passed(continuity, "attention_reliability_evidence"),
        ),
        (
            "operator_reviewed_policy_boundary",
            _passed(continuity, "operator_reviewed_policy_proposals")
            and _passed(continuity, "policy_not_applied"),
        ),
        ("privacy_hidden_reasoning_boundary", privacy_ok),
        (
            "selected_attention_and_downstream_authority_separation",
            authority_inert
            and _passed(intake, "salience_candidate_attention_separation")
            and _passed(deliberation, "attention_not_selected")
            and _passed(continuity, "attention_not_selected"),
        ),
        (
            "source_runtime_and_desktop_boundary",
            not _inside(runtime, source)
            and not runtime_mutated
            and not source_modified
            and intake.get("desktop_verification") == "pending"
            and deliberation.get("desktop_verification") == "pending"
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
        "status": "ready_for_desktop_verification" if ready else "pending_desktop_verification",
        "contract_version": CONTRACT_VERSION,
        "headline": (
            "Reflective attention and salience governance preserves content-free salience intake, "
            "bounded deterministic review, durable outcome continuity, reliability restraint, and "
            "operator-reviewed policy boundaries without selecting attention or granting downstream authority."
        ),
        "epistemic_status": "candidate_artificial_consciousness_not_proven",
        "consciousness_claimed": False,
        "checks": rows,
        "check_count": len(rows),
        "summary": {
            "signal_count": intake_summary.get("signal_count", 0),
            "candidate_count": intake_summary.get("candidate_count", 0),
            "suppressed_candidate_count": intake_summary.get("suppressed_candidate_count", 0),
            "session_count": deliberation_summary.get("session_count", 0),
            "outcome_count": continuity_summary.get("outcome_count", 0),
            "reviewed_candidate_count": continuity_summary.get("reviewed_candidate_count", 0),
            "reflective_attention_salience_intake": intake_summary,
            "reflective_attention_deliberation": deliberation_summary,
            "reflective_attention_continuity_review": continuity_summary,
        },
        "runtime_external": not _inside(runtime, source),
        "runtime_mutated": runtime_mutated,
        "source_modified": source_modified,
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
        "attention_selected": False,
        "reflection_created": False,
        "intention_created": False,
        "initiative_created": False,
        "message_sent": False,
        "notification_created": False,
        "provider_contacted": False,
        "browsing_performed": False,
        "schedule_mutated": False,
        "policy_applied": False,
        "proposal_created": False,
        "proposal_applied": False,
        "approval_granted": False,
        "authorization_granted": False,
        "external_action_executed": False,
        "release_approved": False,
        "release_promoted": False,
        "release_certified": False,
        "desktop_verification_status": "pending",
        "reflective_attention_salience_intake": intake,
        "reflective_attention_deliberation": deliberation,
        "reflective_attention_continuity_review": continuity,
    }
