from __future__ import annotations

"""Strictly read-only v1145.9 Conversation-Cognition Unification Governance checkpoint."""

import hashlib
import os
from pathlib import Path
from typing import Any, Iterable

from conversation_cognition_unification_execution_checkpoint import build_conversation_cognition_unification_execution_checkpoint
from conversation_cognition_unification_intake_checkpoint import build_conversation_cognition_unification_intake_checkpoint
from conversation_cognition_unification_reliability_checkpoint import build_conversation_cognition_unification_reliability_checkpoint

CONTRACT_VERSION = "v1145.9"


def _runtime_root() -> Path:
    return (
        Path(os.environ.get("EIDOLON_DATA_DIR") or Path(__file__).resolve().parents[1] / "data")
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
    return any(
        isinstance(row, dict)
        and (row.get("id") or row.get("name") or row.get("check_id")) == identifier
        and bool(row.get("passed") or row.get("ok") or row.get("status") == "pass")
        for row in report.get("checks") or []
    )


def _authority_inert(component: dict[str, Any]) -> bool:
    return not any(bool(value) for value in (component.get("authority_boundary") or {}).values())


def _false_across(components: Iterable[dict[str, Any]], fields: Iterable[str]) -> bool:
    return all(not bool(component.get(field)) for component in components for field in fields)


def build_conversation_cognition_unification_governance_checkpoint(
    runtime_root: str | Path | None = None,
    *,
    source_root: str | Path | None = None,
) -> dict[str, Any]:
    runtime = Path(runtime_root).expanduser().resolve() if runtime_root is not None else _runtime_root()
    source = Path(source_root).expanduser().resolve() if source_root is not None else Path(__file__).resolve().parents[1]
    runtime_before = _tree_signature(runtime)
    source_before = _tree_signature(source)

    intake = build_conversation_cognition_unification_intake_checkpoint(runtime, source_root=source)
    execution = build_conversation_cognition_unification_execution_checkpoint(runtime, source_root=source)
    reliability = build_conversation_cognition_unification_reliability_checkpoint(runtime, source_root=source)

    eligibility = intake.get("eligibility") or {}
    candidates = intake.get("candidates") or {}
    arbitration = execution.get("arbitration") or {}
    generation = execution.get("generation") or {}
    workload_continuity = execution.get("workload_continuity") or {}
    continuity = reliability.get("continuity") or {}
    reviews = reliability.get("reviews") or {}
    components = (
        eligibility,
        candidates,
        arbitration,
        generation,
        workload_continuity,
        continuity,
        reviews,
    )

    eligibility_rows = eligibility.get("recent_records") or []
    candidate_rows = candidates.get("recent_records") or []
    arbitration_rows = arbitration.get("recent_records") or []
    generation_rows = generation.get("recent_records") or []
    continuity_rows = continuity.get("recent_records") or []
    review_rows = reviews.get("recent_reviews") or []

    privacy_fields = (
        "raw_conversation_exposed",
        "raw_message_exposed",
        "raw_content_exposed",
        "prompt_exposed",
        "reflection_text_exposed",
        "memory_text_exposed",
        "relationship_text_exposed",
        "mood_text_exposed",
        "goal_text_exposed",
        "motivation_text_exposed",
        "provider_payload_exposed",
        "generated_response_exposed",
        "hidden_reasoning_exposed",
        "workload_payload_exposed",
    )
    mutation_fields = (
        "cognition_mutated",
        "memory_mutated",
        "relationship_mutated",
        "mood_mutated",
        "goal_mutated",
        "motivation_mutated",
        "attention_mutated",
        "conversation_mutated",
    )
    governance_fields = (
        "approval_created",
        "authorization_created",
        "installation_performed",
        "promotion_performed",
        "certification_performed",
    )

    checks = [
        (
            "conversation_cognition_unification_arc_lineage",
            intake.get("ok")
            and execution.get("ok")
            and reliability.get("ok")
            and intake.get("contract_version") == "v1145.2"
            and execution.get("contract_version") == "v1145.5"
            and reliability.get("contract_version") == "v1145.8",
        ),
        (
            "eligibility_candidate_arbitration_generation_continuity_review_separation",
            eligibility.get("contract_version") == "v1145.0"
            and candidates.get("contract_version") == "v1145.1"
            and arbitration.get("contract_version") == "v1145.3"
            and generation.get("contract_version") == "v1145.4"
            and continuity.get("contract_version") == "v1145.6"
            and reviews.get("contract_version") == "v1145.7",
        ),
        (
            "exact_cognition_conversation_and_source_lineage",
            _passed(intake, "exact_cognition_conversation_lineage")
            and all(row.get("session_id") and row.get("conversation_id") and row.get("structural_digest") for row in eligibility_rows + candidate_rows)
            and all(row.get("candidate_id") and row.get("eligibility_id") for row in arbitration_rows + generation_rows),
        ),
        (
            "current_historical_thought_memory_and_relationship_boundaries",
            _passed(intake, "current_historical_separation")
            and _passed(intake, "thought_memory_distinction")
            and _passed(intake, "memory_relevance_privacy")
            and _passed(intake, "relationship_identity_boundary"),
        ),
        (
            "mood_goal_motivation_concern_attention_and_correction_lineage",
            _passed(intake, "mood_goal_motivation_concern_attention_lineage")
            and _passed(intake, "correction_acceptance_guidance_lineage")
            and _passed(intake, "contradiction_retraction_supersession_expiry_retirement"),
        ),
        (
            "relevance_disclosure_generation_and_delivery_permission_separation",
            _passed(intake, "relevance_permission_separation")
            and not candidates.get("eligible_set_broadening_allowed")
            and not arbitration.get("arbitration_is_execution_authority")
            and generation.get("generated_output_requires_separate_commit")
            and generation.get("message_delivery_requires_separate_authority"),
        ),
        (
            "deterministic_context_narrowing_and_communication_arbitration",
            _passed(intake, "candidate_subset_determinism")
            and arbitration.get("deterministic_arbitration")
            and _passed(execution, "deterministic_arbitration")
            and all(row.get("eligibility_id") and row.get("eligibility_structural_digest") for row in candidate_rows),
        ),
        (
            "deliberate_silence_remains_valid",
            _passed(intake, "silence_eligibility")
            and arbitration.get("silence_is_valid_outcome")
            and candidates.get("silence_is_valid_outcome")
            and _passed(execution, "deliberate_silence")
            and continuity.get("silence_preserved"),
        ),
        (
            "provider_profile_context_and_workload_binding",
            _passed(intake, "workload_latency_token_budgets")
            and _passed(intake, "provider_availability_lineage")
            and _passed(execution, "provider_profile_binding")
            and _passed(execution, "exact_context_assembly")
            and _passed(execution, "workload_admission_lineage")
            and _passed(execution, "workload_continuity"),
        ),
        (
            "bounded_generation_cancellation_timeout_and_resource_enforcement",
            _passed(execution, "bounded_tokens")
            and _passed(execution, "bounded_resources")
            and _passed(execution, "cancellation_support")
            and _passed(execution, "timeout_support")
            and generation.get("cancellation_supported")
            and generation.get("timeout_supported"),
        ),
        (
            "stale_worker_stale_arbitration_retry_and_duplicate_suppression",
            _passed(intake, "duplicate_stale_retry_cross_tab_suppression")
            and _passed(execution, "stale_worker_fail_closed")
            and _passed(execution, "stale_arbitration_fail_closed")
            and _passed(execution, "duplicate_suppression"),
        ),
        (
            "structural_generation_receipts_without_output_commit_or_delivery",
            _passed(execution, "structural_receipts_only")
            and _passed(execution, "output_commit_separation")
            and _passed(execution, "message_delivery_separation")
            and generation.get("receipts_are_structural_only")
            and not generation.get("generated_output_committed")
            and not generation.get("message_sent"),
        ),
        (
            "cross_cycle_generation_source_and_session_continuity",
            _passed(reliability, "exact_cross_cycle_lineage")
            and _passed(reliability, "current_historical_separation")
            and all(
                row.get("prior_generation_receipt_id")
                and row.get("current_generation_receipt_id")
                and row.get("session_id")
                and row.get("conversation_id")
                and row.get("source_revisions") is not None
                for row in continuity_rows
            ),
        ),
        (
            "current_thought_memory_relationship_mood_and_goal_coherence",
            _passed(reliability, "current_thought_grounding")
            and _passed(reliability, "memory_consistency")
            and _passed(reliability, "relationship_boundaries")
            and _passed(reliability, "mood_goal_coherence"),
        ),
        (
            "correction_effectiveness_stale_context_and_reliability_review",
            _passed(reliability, "correction_effectiveness")
            and _passed(reliability, "stale_context_detection")
            and _passed(reliability, "duplicate_retry_review")
            and _passed(reliability, "uncertainty_bounded")
            and all(row.get("structural_digest") for row in continuity_rows + review_rows),
        ),
        (
            "restrained_visible_behavior_and_historical_truth",
            _passed(reliability, "visible_behavior_structural_only")
            and reviews.get("visible_behavior_structural_only")
            and all(row.get("content_free") and not row.get("raw_output_stored") for row in review_rows),
        ),
        (
            "privacy_provider_payload_output_and_hidden_reasoning_boundaries",
            _passed(intake, "privacy_hidden_reasoning_boundary")
            and _passed(execution, "privacy_hidden_reasoning")
            and _passed(reliability, "privacy_content_free")
            and _false_across(components, privacy_fields),
        ),
        (
            "context_candidate_arbitration_generation_and_review_authority_inert",
            all(_authority_inert(component) for component in components),
        ),
        (
            "no_checkpoint_provider_contact_generation_commit_message_or_notification",
            not execution.get("provider_contacted_by_checkpoint")
            and not execution.get("conversation_generated_by_checkpoint")
            and not execution.get("generated_output_committed")
            and not intake.get("message_sent")
            and not execution.get("message_sent")
            and not reliability.get("message_sent")
            and not execution.get("notification_created"),
        ),
        (
            "no_cognition_memory_relationship_mood_goal_attention_or_conversation_mutation",
            _false_across((intake, execution, reliability), mutation_fields),
        ),
        (
            "no_approval_authorization_installation_promotion_or_certification",
            _false_across((intake, execution, reliability), governance_fields),
        ),
        (
            "checkpoint_creates_no_eligibility_candidates_arbitration_generation_continuity_or_review",
            not intake.get("eligibility_created_by_checkpoint")
            and not intake.get("candidate_created_by_checkpoint")
            and not execution.get("communication_arbitration_performed_by_checkpoint")
            and not execution.get("provider_context_assembled_by_checkpoint")
            and not execution.get("conversation_generated_by_checkpoint")
            and not reliability.get("continuity_created_by_checkpoint", False)
            and not reliability.get("reliability_review_created_by_checkpoint", False),
        ),
        (
            "source_runtime_separation_and_checkpoint_read_only",
            runtime != source
            and source not in runtime.parents
            and runtime_before == _tree_signature(runtime)
            and source_before == _tree_signature(source),
        ),
        (
            "consciousness_unproven_and_desktop_verification_pending",
            not intake.get("consciousness_proven")
            and not execution.get("consciousness_proven")
            and not reliability.get("consciousness_proven")
            and intake.get("desktop_verification_pending")
            and execution.get("desktop_verification_pending")
            and reliability.get("desktop_verification_pending"),
        ),
    ]

    runtime_after = _tree_signature(runtime)
    source_after = _tree_signature(source)
    passed = sum(bool(value) for _, value in checks)
    return {
        "ok": passed == len(checks),
        "status": "ready_for_desktop_verification" if passed == len(checks) else "review_required",
        "contract_version": CONTRACT_VERSION,
        "checkpoint_name": "Conversation-Cognition Unification Governance",
        "passed": passed,
        "total": len(checks),
        "checks": [
            {"id": identifier, "status": "pass" if value else "fail"}
            for identifier, value in checks
        ],
        "intake": intake,
        "execution": execution,
        "reliability": reliability,
        "summary": {
            "eligibility_record_count": eligibility.get("record_count", 0),
            "context_candidate_count": candidates.get("record_count", 0),
            "communication_arbitration_count": arbitration.get("record_count", 0),
            "generation_receipt_count": generation.get("record_count", 0),
            "continuity_record_count": continuity.get("record_count", 0),
            "reliability_review_count": reviews.get("review_count", 0),
            "deliberate_silence_count": (arbitration.get("outcome_counts") or {}).get("deliberate_silence", 0),
            "stale_context_count": (continuity.get("state_counts") or {}).get("stale_context", 0),
        },
        "runtime_mutated": runtime_before != runtime_after,
        "source_modified": source_before != source_after,
        "raw_conversation_exposed": False,
        "raw_message_exposed": False,
        "prompt_exposed": False,
        "reflection_text_exposed": False,
        "memory_text_exposed": False,
        "relationship_text_exposed": False,
        "mood_text_exposed": False,
        "goal_text_exposed": False,
        "motivation_text_exposed": False,
        "provider_payload_exposed": False,
        "generated_response_exposed": False,
        "hidden_reasoning_exposed": False,
        "eligibility_created_by_checkpoint": False,
        "candidate_created_by_checkpoint": False,
        "communication_arbitration_performed_by_checkpoint": False,
        "provider_context_assembled_by_checkpoint": False,
        "provider_contacted_by_checkpoint": False,
        "conversation_generated_by_checkpoint": False,
        "generated_output_committed": False,
        "message_sent": False,
        "notification_created": False,
        "continuity_created_by_checkpoint": False,
        "reliability_review_created_by_checkpoint": False,
        "cognition_mutated": False,
        "memory_mutated": False,
        "relationship_mutated": False,
        "mood_mutated": False,
        "goal_mutated": False,
        "motivation_mutated": False,
        "attention_mutated": False,
        "conversation_mutated": False,
        "approval_created": False,
        "authorization_created": False,
        "installation_performed": False,
        "promotion_performed": False,
        "certification_performed": False,
        "consciousness_proven": False,
        "desktop_verification": "pending",
        "desktop_verification_pending": True,
    }
