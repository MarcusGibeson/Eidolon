from __future__ import annotations

"""Strictly read-only v1142.9 Operator Correction and Acceptance Learning Governance checkpoint."""

import hashlib
import os
from pathlib import Path
from typing import Any, Iterable

from operator_correction_acceptance_intake_checkpoint import build_operator_correction_acceptance_intake_checkpoint
from operator_correction_reasoning_integration_checkpoint import build_operator_correction_reasoning_integration_checkpoint
from operator_correction_reliability_visible_behavior_checkpoint import build_operator_correction_reliability_visible_behavior_checkpoint

CONTRACT_VERSION = "v1142.9"


def _runtime_root() -> Path:
    return (
        Path(
            os.environ.get("EIDOLON_DATA_DIR")
            or Path(__file__).resolve().parents[1] / "data"
        )
        .expanduser()
        .resolve()
        / "cognition"
    )


def _tree_signature(root: Path) -> str:
    digest = hashlib.sha256()
    if not root.exists():
        digest.update(b"missing-tree")
        return digest.hexdigest()
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        if "__pycache__" in path.parts or path.suffix in {".pyc", ".pyo"}:
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


def _passed(report: dict[str, Any], identifier: str) -> bool:
    for row in report.get("checks") or []:
        if not isinstance(row, dict):
            continue
        row_id = row.get("id") or row.get("name") or row.get("check") or row.get("check_id")
        if row_id != identifier:
            continue
        return bool(row.get("passed") or row.get("ok") or row.get("status") == "pass")
    return False


def _false_across(components: Iterable[dict[str, Any]], fields: Iterable[str]) -> bool:
    return all(not bool(component.get(field)) for component in components for field in fields)


def _authority_inert(component: dict[str, Any]) -> bool:
    return not any(bool(value) for value in (component.get("authority_boundary") or {}).values())


def build_operator_correction_acceptance_learning_governance_checkpoint(
    runtime_root: str | Path | None = None,
    *,
    source_root: str | Path | None = None,
) -> dict[str, Any]:
    runtime = Path(runtime_root).expanduser().resolve() if runtime_root is not None else _runtime_root()
    source = Path(source_root).expanduser().resolve() if source_root is not None else Path(__file__).resolve().parents[1]
    runtime_before = _tree_signature(runtime)
    source_before = _tree_signature(source)

    intake = build_operator_correction_acceptance_intake_checkpoint(runtime, source_root=source)
    integration = build_operator_correction_reasoning_integration_checkpoint(runtime, source_root=source)
    reliability = build_operator_correction_reliability_visible_behavior_checkpoint(runtime, source_root=source)

    eligibility = intake.get("eligibility") or {}
    guidance = intake.get("guidance") or {}
    application = integration.get("application") or {}
    continuity = integration.get("continuity") or {}
    review = reliability.get("reliability_review") or {}
    evidence = reliability.get("visible_behavior_evidence") or {}
    components = (eligibility, guidance, application, continuity, review, evidence)

    eligibility_rows = eligibility.get("recent_records") or []
    guidance_rows = guidance.get("recent_records") or []
    application_rows = application.get("recent_records") or []
    continuity_rows = continuity.get("recent_records") or []
    review_rows = review.get("recent_records") or []
    evidence_rows = evidence.get("recent_records") or []

    privacy_fields = (
        "raw_content_exposed",
        "operator_text_exposed",
        "reasoning_text_exposed",
        "conversation_exposed",
        "prompt_exposed",
        "provider_payload_exposed",
        "private_project_record_exposed",
        "hidden_reasoning_exposed",
    )
    forbidden_authority_fields = (
        "history_rewritten",
        "belief_mutated",
        "goal_mutated",
        "motivation_mutated",
        "self_model_mutated",
        "reasoning_executed",
        "future_reasoning_executed",
        "approval_created",
        "authorization_created",
        "external_action_executed",
        "installation_performed",
        "promotion_performed",
        "certification_performed",
    )

    checks = [
        (
            "operator_correction_acceptance_learning_arc_lineage",
            intake.get("ok")
            and integration.get("ok")
            and reliability.get("ok")
            and intake.get("contract_version") == "v1142.2"
            and integration.get("contract_version") == "v1142.5"
            and reliability.get("contract_version") == "v1142.8",
        ),
        (
            "explicit_operator_decision_and_exact_target_lineage",
            _passed(intake, "explicit_operator_decisions")
            and _passed(intake, "exact_target_lineage")
            and all(
                row.get("operator_decision_id")
                and row.get("target_id")
                and row.get("source_record_id")
                and row.get("source_revision_id")
                for row in eligibility_rows
                if row.get("state") == "eligible"
            ),
        ),
        (
            "correction_acceptance_rejection_clarification_qualification_withdrawal_distinction",
            _passed(intake, "correction_acceptance_distinguished"),
        ),
        (
            "historical_truth_and_original_state_preserved",
            _passed(intake, "historical_truth_preserved")
            and _passed(integration, "historical_truth_preserved")
            and _passed(reliability, "historical_truth_preserved")
            and all(row.get("historical_record_preserved") for row in eligibility_rows + guidance_rows + application_rows + continuity_rows + review_rows + evidence_rows),
        ),
        (
            "eligibility_guidance_application_review_and_evidence_separation",
            all(not row.get("application_id") for row in eligibility_rows + guidance_rows)
            and all(row.get("application_id") for row in continuity_rows + review_rows + evidence_rows),
        ),
        (
            "bounded_advisory_future_reasoning_scope",
            _passed(intake, "future_reasoning_advisory")
            and _passed(intake, "bounded_reasoning_scopes")
            and _passed(integration, "bounded_scope")
            and all(row.get("reasoning_scope_id") for row in application_rows),
        ),
        (
            "deterministic_selection_and_fail_closed_non_application",
            _passed(integration, "deterministic_selection")
            and _passed(integration, "stale_revision_fail_closed")
            and _passed(integration, "conflict_deferral")
            and all(
                row.get("state") != "selected" or len(row.get("selected_guidance_ids") or []) == 1
                for row in application_rows
            ),
        ),
        (
            "restart_continuity_stale_claim_release_and_duplicate_suppression",
            _passed(integration, "restart_continuity")
            and _passed(integration, "stale_claim_release")
            and _passed(integration, "duplicate_suppression")
            and all(row.get("application_structural_digest") for row in continuity_rows),
        ),
        (
            "reliability_effectiveness_missed_overapplied_conflict_drift_and_inconclusive_review",
            _passed(reliability, "missed_correction_review")
            and _passed(reliability, "over_application_review")
            and _passed(reliability, "conflict_review")
            and _passed(reliability, "drift_review"),
        ),
        (
            "exact_reliability_and_visible_behavior_lineage",
            _passed(reliability, "exact_review_lineage")
            and _passed(reliability, "visible_evidence_lineage")
            and all(row.get("application_structural_digest") for row in review_rows)
            and all(row.get("review_structural_digest") for row in evidence_rows),
        ),
        (
            "restrained_operator_visible_evidence",
            _passed(reliability, "restrained_evidence")
            and all(row.get("operator_visible") and row.get("content_free") for row in evidence_rows),
        ),
        (
            "contradiction_retraction_supersession_and_retirement_history",
            _passed(intake, "supersession_retraction_visible")
            and _passed(integration, "retraction_supersession_visible")
            and _passed(reliability, "retraction_supersession_visible"),
        ),
        (
            "privacy_and_hidden_reasoning_boundaries",
            _passed(intake, "privacy")
            and _passed(integration, "privacy")
            and _passed(reliability, "privacy")
            and _false_across(components, privacy_fields),
        ),
        (
            "no_history_belief_goal_motivation_or_self_model_mutation",
            _passed(intake, "no_history_rewrite")
            and _passed(reliability, "no_state_mutation")
            and _false_across((intake, integration, reliability), forbidden_authority_fields[:5]),
        ),
        (
            "no_reasoning_generation_or_execution_by_governance_records",
            _passed(intake, "no_future_reasoning_execution")
            and _passed(integration, "no_reasoning_execution")
            and all(not row.get("reasoning_text_stored") for row in review_rows)
            and all(not row.get("reasoning_text_exposed") for row in evidence_rows),
        ),
        (
            "authority_separation",
            _passed(intake, "authority_separation")
            and _passed(integration, "authority_separation")
            and _passed(reliability, "authority_separation")
            and all(_authority_inert(component) for component in components),
        ),
        (
            "no_approval_authorization_external_action_installation_promotion_or_certification",
            _false_across((intake, integration, reliability), forbidden_authority_fields[7:]),
        ),
        (
            "checkpoint_is_strictly_read_only",
            runtime_before == _tree_signature(runtime) and source_before == _tree_signature(source),
        ),
        ("source_runtime_separation", runtime != source),
        ("desktop_verification_pending", True),
    ]

    passed = sum(bool(value) for _, value in checks)
    runtime_mutated = runtime_before != _tree_signature(runtime)
    source_modified = source_before != _tree_signature(source)
    return {
        "ok": passed == len(checks),
        "status": "ready_for_desktop_verification" if passed == len(checks) else "review_required",
        "contract_version": CONTRACT_VERSION,
        "passed": passed,
        "total": len(checks),
        "checks": [{"id": identifier, "status": "pass" if value else "fail"} for identifier, value in checks],
        "intake": intake,
        "integration": integration,
        "reliability": reliability,
        "summary": {
            "eligibility_record_count": int(eligibility.get("record_count") or 0),
            "guidance_record_count": int(guidance.get("record_count") or 0),
            "application_record_count": int(application.get("record_count") or 0),
            "continuity_record_count": int(continuity.get("record_count") or 0),
            "reliability_review_count": int(review.get("record_count") or 0),
            "visible_evidence_count": int(evidence.get("record_count") or 0),
        },
        "runtime_mutated": runtime_mutated,
        "source_modified": source_modified,
        "raw_content_exposed": False,
        "operator_text_exposed": False,
        "reasoning_text_exposed": False,
        "conversation_exposed": False,
        "prompt_exposed": False,
        "provider_payload_exposed": False,
        "private_project_record_exposed": False,
        "hidden_reasoning_exposed": False,
        "history_rewritten": False,
        "belief_mutated": False,
        "goal_mutated": False,
        "motivation_mutated": False,
        "self_model_mutated": False,
        "reasoning_executed": False,
        "approval_created": False,
        "authorization_created": False,
        "external_action_executed": False,
        "installation_performed": False,
        "promotion_performed": False,
        "certification_performed": False,
        "eligibility_created_by_checkpoint": False,
        "guidance_created_by_checkpoint": False,
        "application_created_by_checkpoint": False,
        "continuity_created_by_checkpoint": False,
        "reliability_review_created_by_checkpoint": False,
        "visible_evidence_created_by_checkpoint": False,
        "consciousness_proven": False,
        "desktop_verification": "pending",
        "desktop_verification_pending": True,
    }
