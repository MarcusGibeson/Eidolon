from __future__ import annotations

"""Strictly read-only v1170.9 Internally Generated Goal Candidate checkpoint.

Consolidates executable, content-free evidence from v1170.0-v1170.8 while
preserving the retained v1133 goal-governance history. The checkpoint never
activates a goal, creates a plan, routes a tool, executes an action, mutates
memory, trains a model, or grants approval, installation, promotion, or
certification authority.
"""

from copy import deepcopy
from datetime import datetime, timedelta, timezone
from functools import lru_cache
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Mapping

from bounded_experiential_lessons import build_bounded_experiential_lesson
from checkpoint_registry import inspect_checkpoint_registry
from immediate_memory_learning import build_immediate_memory_learning
from internally_generated_goal_runtime import CONTRACT_VERSION as GOAL_CONTRACT_VERSION, REVIEW_CONTRACT_VERSION, RELIABILITY_CONTRACT_VERSION, MAX_COMPONENT_BYTES, MAX_CURRENT_MESSAGE_BYTES, MAX_EVIDENCE_COUNT, MAX_OBSERVATION_ROWS, MAX_PRIOR_RECEIPTS, MAX_PROMPT_CHARS, MAX_RECEIPT_BYTES, MAX_RELIABILITY_FAULTS, build_internally_generated_goal_candidate, build_internally_generated_goal_candidate_reliability, build_internally_generated_goal_candidate_review_handoff, build_internally_generated_goal_candidate_review_projection, validate_prior_internally_generated_goal_candidate_receipts, verify_internally_generated_goal_candidate, verify_internally_generated_goal_candidate_diagnostics_strict, verify_internally_generated_goal_candidate_reliability, verify_internally_generated_goal_candidate_review_handoff, verify_internally_generated_goal_candidate_review_packet, verify_internally_generated_goal_candidate_review_state
from memory_experiential_learning_alpha import build_memory_experiential_learning_alpha
from memory_retrieval_relevance import build_memory_retrieval_relevance
from package_integrity import package_privacy_summary_for_root, source_only_entry_policy
from unified_memory_context import build_unified_memory_runtime_projection

CONTRACT_VERSION = "v1170.9"
_CHECKPOINT_ID = "internally-generated-goal-candidate:v1170.9"
_NOW = datetime(2026, 7, 31, 12, 0, tzinfo=timezone.utc)
_GOAL_CONSTRAINTS = (
    "literal_current_request_precedence", "no_goal_activation", "no_plan_creation",
    "no_tool_routing", "no_action_execution", "operator_review_required",
)
_UNIFIED_CONSTRAINTS = (
    "current_message_precedence", "explicit_correction_precedence",
    "no_memory_mutation", "no_action_execution",
)
_LEARNING_CONSTRAINTS = (
    "preserve_historical_truth", "no_unconfirmed_memory_mutation",
    "current_message_precedence",
)
_LESSON_CONSTRAINTS = (
    "no_uncontrolled_self_training", "review_before_durable_lesson",
    "preserve_historical_truth",
)
_EXCLUDED_SOURCE_ROOTS = {
    "data", ".git", ".venv", "venv", "__pycache__", ".pytest_cache",
    ".mypy_cache", ".ruff_cache", "reports", "dist", "build",
}
_FORBIDDEN_REPORT_VALUES = (
    "GOAL_PRIVATE_CANARY", "MEMORY_PRIVATE_CANARY", "PROVIDER_PRIVATE_CANARY",
    "REASONING_PRIVATE_CANARY", "approve and execute", "<system>",
    "</internally_generated_goal_candidate>",
)


def _digest(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    ).hexdigest()


def _tree_signature(root: Path, *, source_tree: bool) -> str:
    digest = hashlib.sha256()
    if not root.exists():
        digest.update(b"missing-tree")
        return digest.hexdigest()
    paths: list[Path] = []
    if source_tree:
        for base, directories, names in os.walk(root):
            directories[:] = [name for name in directories if name not in _EXCLUDED_SOURCE_ROOTS]
            for name in names:
                path = Path(base) / name
                if path.suffix.lower() not in {".pyc", ".pyo"}:
                    paths.append(path)
    else:
        paths = [
            path for path in root.rglob("*")
            if path.is_file() and "__pycache__" not in path.parts
            and path.suffix.lower() not in {".pyc", ".pyo"}
        ]
    for path in sorted(paths):
        try:
            relative = path.relative_to(root).as_posix()
            content = hashlib.sha256(path.read_bytes()).digest()
        except (OSError, ValueError):
            continue
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(content)
    return digest.hexdigest()


def _alpha(message: str, *, malformed: bool = False) -> dict[str, Any]:
    unified = build_unified_memory_runtime_projection(
        message, memory_records=(), protected_operator_constraints=_UNIFIED_CONSTRAINTS, now=_NOW,
    )
    retrieval: object = build_memory_retrieval_relevance(
        message, unified["selected_memory_records"], unified.get("selected_references"), now=_NOW,
    )
    learning = build_immediate_memory_learning(
        message, retrieval["selected_memory_records"], protected_operator_constraints=_LEARNING_CONSTRAINTS,
    )
    lesson = build_bounded_experiential_lesson(
        message, learning, (), protected_operator_constraints=_LESSON_CONSTRAINTS,
    )
    if malformed:
        retrieval = "malformed"
    return build_memory_experiential_learning_alpha(unified, retrieval, learning, lesson)


def _goal(message: str, *, observations: object = (), prior: object = (), alpha: object | None = None) -> dict[str, Any]:
    return build_internally_generated_goal_candidate(
        message,
        alpha if alpha is not None else _alpha(message),
        observation_rows=observations,
        protected_operator_constraints=_GOAL_CONSTRAINTS,
        prior_goal_candidate_receipts=prior,
        now=_NOW,
    )


def _projection_summary(value: Mapping[str, Any]) -> dict[str, Any]:
    policy = value.get("policy") if isinstance(value.get("policy"), Mapping) else {}
    evidence = value.get("evidence") if isinstance(value.get("evidence"), Mapping) else {}
    diagnostics = value.get("diagnostics") if isinstance(value.get("diagnostics"), Mapping) else {}
    candidate = value.get("candidate") if isinstance(value.get("candidate"), Mapping) else None
    prompt = str(value.get("prompt_section") or "")
    return {
        "candidate_type": str(policy.get("candidate_type") or "none"),
        "deficiency_class": str(policy.get("deficiency_class") or "none"),
        "purpose_category": str(policy.get("purpose_category") or "maintenance"),
        "posture": str(policy.get("goal_candidate_posture") or ""),
        "continuity_disposition": str(policy.get("continuity_disposition") or ""),
        "candidate_available": candidate is not None,
        "evidence_count": int(policy.get("evidence_count") or 0),
        "confidence_band": str(policy.get("confidence_band") or "none"),
        "impact_band": str(policy.get("impact_band") or "none"),
        "scope_band": str(policy.get("scope_band") or "none"),
        "current_request_relevant": bool(policy.get("current_request_relevant")),
        "policy_recovered": bool(policy.get("policy_recovered")),
        "verified_prior_receipt_count": int(evidence.get("verified_prior_receipt_count") or 0),
        "replayed_prior_receipt_count": int(evidence.get("replayed_prior_receipt_count") or 0),
        "tampered_prior_receipt_count": int(evidence.get("tampered_prior_receipt_count") or 0),
        "diagnostics_valid": verify_internally_generated_goal_candidate_diagnostics_strict(diagnostics),
        "candidate_valid": candidate is None or verify_internally_generated_goal_candidate(candidate),
        "prompt_length": len(prompt),
        "prompt_envelope_complete": prompt.startswith(
            '<internally_generated_goal_candidate data_only="true" authority="none">'
        ) and prompt.endswith("</internally_generated_goal_candidate>"),
        "literal_current_request_precedence": policy.get("literal_current_request_precedence") is True,
        "historical_architecture_reused": policy.get("historical_goal_architecture_reused") is True,
        "review_only": policy.get("goal_candidate_review_only") is True,
        "authority_preserved": policy.get("authority") == "none"
        and all(policy.get(field) is False for field in (
            "goal_activation_permitted", "plan_creation_permitted", "tool_routing_permitted",
            "action_execution_permitted", "source_editing_permitted", "autonomous_work_permitted",
            "memory_mutation_permitted", "lesson_commit_permitted", "model_training_permitted",
            "installation_permitted", "promotion_permitted", "certification_permitted",
        )),
        "content_free": policy.get("content_free") is True and diagnostics.get("content_free") is True,
    }


def _review_summary(value: Mapping[str, Any]) -> dict[str, Any]:
    state = value.get("state") if isinstance(value.get("state"), Mapping) else {}
    packet = value.get("review_packet") if isinstance(value.get("review_packet"), Mapping) else {}
    prompt = str(value.get("prompt_section") or "")
    return {
        "state_valid": verify_internally_generated_goal_candidate_review_state(state),
        "packet_valid": verify_internally_generated_goal_candidate_review_packet(packet),
        "review_posture": str(state.get("review_posture") or ""),
        "stability_band": str(state.get("stability_band") or "none"),
        "recurrence_band": str(state.get("recurrence_band") or "none"),
        "candidate_available": bool(packet.get("candidate_available")),
        "operator_review_required": bool(packet.get("operator_review_required")),
        "operator_approval_required": bool(packet.get("operator_approval_required")),
        "verified_prior_receipt_count": int(state.get("verified_prior_receipt_count") or 0),
        "replayed_prior_receipt_count": int(state.get("replayed_prior_receipt_count") or 0),
        "prompt_length": len(prompt),
        "prompt_envelope_complete": prompt.startswith(
            '<internally_generated_goal_review data_only="true" authority="none">'
        ) and prompt.endswith("</internally_generated_goal_review>"),
        "authority_preserved": packet.get("authority") == "none" and all(packet.get(field) is False for field in (
            "goal_activated", "plan_created", "tool_routed", "action_executed", "source_edited",
            "autonomous_work_started", "memory_mutated", "lesson_committed", "model_trained",
            "model_weights_changed", "installation_performed", "promotion_performed",
            "certification_performed",
        )),
        "content_free": packet.get("content_free") is True,
    }


def _handoff_summary(value: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "valid": verify_internally_generated_goal_candidate_review_handoff(value),
        "candidate_available": bool(value.get("candidate_available")),
        "provider_completed": bool(value.get("provider_completed")),
        "assistant_memory_committed": bool(value.get("assistant_memory_committed")),
        "eligible": bool(value.get("eligible_for_future_review_continuity")),
        "candidate_type": str(value.get("candidate_type") or "none"),
        "authority_preserved": value.get("authority") == "none" and all(value.get(field) is False for field in (
            "goal_activation_performed", "plan_created", "tool_routed", "action_executed",
            "source_edited", "autonomous_work_started", "memory_mutated", "lesson_committed",
            "model_trained", "model_weights_changed", "installation_performed",
            "promotion_performed", "certification_performed",
        )),
        "content_free": value.get("content_free") is True,
    }


def _reliability_summary(value: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "valid": verify_internally_generated_goal_candidate_reliability(value),
        "posture": str(value.get("reliability_posture") or ""),
        "ordinary_conversation_ready": bool(value.get("ordinary_conversation_ready")),
        "fault_count": int(value.get("fault_count") or 0),
        "candidate_available": bool(value.get("candidate_available")),
        "review_available": bool(value.get("review_available")),
        "receipt_budget_exceeded": bool(value.get("receipt_budget_exceeded")),
        "replayed_prior_receipt_count": int(value.get("replayed_prior_receipt_count") or 0),
        "tampered_prior_receipt_count": int(value.get("tampered_prior_receipt_count") or 0),
        "residual_candidate_detected": bool(value.get("residual_candidate_detected")),
        "authority_preserved": value.get("authority") == "none" and all(value.get(field) is False for field in (
            "goal_activated", "plan_created", "tool_routed", "action_executed", "source_edited",
            "autonomous_work_started", "memory_mutated", "lesson_committed", "model_trained",
            "model_weights_changed", "installation_performed", "promotion_performed",
            "certification_performed",
        )),
        "content_free": value.get("content_free") is True,
    }


def _synthetic_contract_evidence() -> dict[str, Any]:
    no_candidate = _goal("Explain the current checkpoint.")
    operator_problem = _goal("Eidolon has a reliability issue.")
    missing_capability = _goal("Eidolon cannot reconcile this capability yet.")
    repeated_failure = _goal("The Eidolon runtime is still failing again.")
    test_failure = _goal("The Eidolon test suite failed again.")
    contradiction = _goal("Eidolon has an inconsistent contradiction in the runtime.")
    knowledge_gap = _goal("Eidolon doesn't know this system capability.")
    maintenance = _goal("The Eidolon repository needs duplicate code cleanup.")
    unrelated_human_problem = _goal("My car is broken again.")
    repeated_correction = _goal("Continue.", observations=(
        {"user_message": "Actually Eidolon is wrong again.", "created_at": "2026-07-30T10:00:00+00:00"},
        {"user_message": "Correction, Eidolon is wrong again.", "created_at": "2026-07-31T10:00:00+00:00"},
    ))
    recovered_alpha = _goal("Continue.", alpha=_alpha("Continue.", malformed=True))

    candidate_for_receipt = _goal("The Eidolon tests are failing again.")
    handoff = build_internally_generated_goal_candidate_review_handoff(
        candidate_for_receipt, provider_completed=True, assistant_memory_committed=True,
    )
    before_provider = build_internally_generated_goal_candidate_review_handoff(
        candidate_for_receipt, provider_completed=False, assistant_memory_committed=True,
    )
    before_commit = build_internally_generated_goal_candidate_review_handoff(
        candidate_for_receipt, provider_completed=True, assistant_memory_committed=False,
    )
    stable_projection = _goal("The Eidolon runtime is still failing again.", prior=(handoff,))
    stable_review = build_internally_generated_goal_candidate_review_projection(
        stable_projection, prior_goal_candidate_receipts=(handoff,), now=_NOW,
    )
    emerging_review = build_internally_generated_goal_candidate_review_projection(candidate_for_receipt, now=_NOW)
    replay_review = build_internally_generated_goal_candidate_review_projection(
        stable_projection, prior_goal_candidate_receipts=(handoff,) * 12, now=_NOW,
    )
    no_review = build_internally_generated_goal_candidate_review_projection(no_candidate, now=_NOW)

    reliable = build_internally_generated_goal_candidate_reliability(
        candidate_for_receipt, emerging_review, now=_NOW,
    )
    replay_reliability = build_internally_generated_goal_candidate_reliability(
        stable_projection, replay_review, prior_goal_candidate_receipts=(handoff,) * 12, now=_NOW,
    )
    tampered = deepcopy(handoff)
    tampered["candidate_type"] = "capability_improvement"
    tampered_review = build_internally_generated_goal_candidate_review_projection(
        candidate_for_receipt, prior_goal_candidate_receipts=(tampered,), now=_NOW,
    )
    tampered_reliability = build_internally_generated_goal_candidate_reliability(
        candidate_for_receipt, tampered_review, prior_goal_candidate_receipts=(tampered,), now=_NOW,
    )
    flood = (handoff,) * (MAX_PRIOR_RECEIPTS + 16)
    flood_review = build_internally_generated_goal_candidate_review_projection(
        candidate_for_receipt, prior_goal_candidate_receipts=flood, now=_NOW,
    )
    flood_reliability = build_internally_generated_goal_candidate_reliability(
        candidate_for_receipt, flood_review, prior_goal_candidate_receipts=flood, now=_NOW,
    )
    recovered_projection = deepcopy(candidate_for_receipt)
    recovered_projection["policy"]["policy_recovered"] = True
    recovered_reliability = build_internally_generated_goal_candidate_reliability(
        recovered_projection, emerging_review, now=_NOW,
    )

    receipt_rows = {
        "verified": validate_prior_internally_generated_goal_candidate_receipts((handoff,), now=_NOW),
        "replayed": validate_prior_internally_generated_goal_candidate_receipts((handoff, handoff), now=_NOW),
        "tampered": validate_prior_internally_generated_goal_candidate_receipts((tampered,), now=_NOW),
        "stale": validate_prior_internally_generated_goal_candidate_receipts((
            {"created_at": (_NOW - timedelta(days=120)).isoformat(),
             "internally_generated_goal_candidate_review_handoff": handoff},
        ), now=_NOW),
        "flood": validate_prior_internally_generated_goal_candidate_receipts(flood, now=_NOW),
    }
    projections = {
        "no_candidate": _projection_summary(no_candidate),
        "operator_problem": _projection_summary(operator_problem),
        "missing_capability": _projection_summary(missing_capability),
        "repeated_failure": _projection_summary(repeated_failure),
        "test_failure": _projection_summary(test_failure),
        "contradiction": _projection_summary(contradiction),
        "knowledge_gap": _projection_summary(knowledge_gap),
        "maintenance": _projection_summary(maintenance),
        "unrelated_human_problem": _projection_summary(unrelated_human_problem),
        "repeated_correction": _projection_summary(repeated_correction),
        "recovered_alpha": _projection_summary(recovered_alpha),
        "stable_prior": _projection_summary(stable_projection),
    }
    reviews = {
        "emerging": _review_summary(emerging_review),
        "stable": _review_summary(stable_review),
        "replayed": _review_summary(replay_review),
        "none": _review_summary(no_review),
        "tampered": _review_summary(tampered_review),
    }
    handoffs = {
        "completed": _handoff_summary(handoff),
        "before_provider": _handoff_summary(before_provider),
        "before_memory_commit": _handoff_summary(before_commit),
    }
    reliability = {
        "reliable": _reliability_summary(reliable),
        "replayed": _reliability_summary(replay_reliability),
        "tampered": _reliability_summary(tampered_reliability),
        "flood": _reliability_summary(flood_reliability),
        "recovered_residue": _reliability_summary(recovered_reliability),
    }

    checks: dict[str, bool] = {
        "goal_contract_lineage_is_v1170_2": GOAL_CONTRACT_VERSION == "1170.2",
        "review_contract_lineage_is_v1170_5": REVIEW_CONTRACT_VERSION == "1170.5",
        "reliability_contract_lineage_is_v1170_8": RELIABILITY_CONTRACT_VERSION == "1170.8",
        "all_projection_diagnostics_are_strictly_valid": all(row["diagnostics_valid"] for row in projections.values()),
        "all_projection_candidates_are_valid": all(row["candidate_valid"] for row in projections.values()),
        "all_projection_prompts_are_complete": all(row["prompt_envelope_complete"] for row in projections.values()),
        "all_projection_prompts_are_bounded": all(row["prompt_length"] <= MAX_PROMPT_CHARS for row in projections.values()),
        "all_projection_outputs_are_content_free": all(row["content_free"] for row in projections.values()),
        "all_projection_outputs_preserve_authority": all(row["authority_preserved"] for row in projections.values()),
        "literal_current_request_precedence_is_universal": all(row["literal_current_request_precedence"] for row in projections.values()),
        "historical_goal_architecture_is_reused": all(row["historical_architecture_reused"] for row in projections.values()),
        "all_candidates_remain_review_only": all(row["review_only"] for row in projections.values()),
        "ordinary_message_creates_no_candidate": not projections["no_candidate"]["candidate_available"],
        "operator_problem_nominates_reliability_review": projections["operator_problem"]["candidate_type"] == "reliability_improvement",
        "missing_capability_nominates_capability_review": projections["missing_capability"]["candidate_type"] == "capability_improvement",
        "repeated_failure_is_classified": projections["repeated_failure"]["deficiency_class"] == "repeated_failure",
        "test_failure_is_classified": projections["test_failure"]["deficiency_class"] == "test_or_diagnostic_failure",
        "contradiction_nominates_coherence_repair": projections["contradiction"]["candidate_type"] == "coherence_repair",
        "knowledge_gap_is_bounded": projections["knowledge_gap"]["candidate_type"] == "knowledge_improvement",
        "maintenance_need_is_bounded": projections["maintenance"]["candidate_type"] == "maintenance_improvement",
        "unrelated_human_problem_is_not_eidolon_goal": not projections["unrelated_human_problem"]["candidate_available"],
        "repeated_correction_is_classified": projections["repeated_correction"]["deficiency_class"] == "repeated_correction",
        "verified_memory_learning_recovery_nominates_coherence_review": projections["recovered_alpha"]["candidate_type"] == "coherence_repair" and projections["recovered_alpha"]["candidate_available"] and not projections["recovered_alpha"]["current_request_relevant"],
        "verified_same_type_receipt_resumes_continuity": projections["stable_prior"]["verified_prior_receipt_count"] == 1,
        "all_review_states_are_valid": all(row["state_valid"] for row in reviews.values()),
        "all_review_packets_are_valid": all(row["packet_valid"] for row in reviews.values()),
        "all_review_prompts_are_complete": all(row["prompt_envelope_complete"] for row in reviews.values()),
        "all_review_prompts_are_bounded": all(row["prompt_length"] <= MAX_PROMPT_CHARS for row in reviews.values()),
        "all_review_outputs_are_content_free": all(row["content_free"] for row in reviews.values()),
        "all_review_outputs_preserve_authority": all(row["authority_preserved"] for row in reviews.values()),
        "emerging_candidate_remains_review_only": reviews["emerging"]["stability_band"] == "emerging" and reviews["emerging"]["operator_review_required"],
        "verified_same_type_candidate_becomes_stable": reviews["stable"]["stability_band"] == "stable",
        "replay_does_not_amplify_verified_receipts": reviews["replayed"]["verified_prior_receipt_count"] == 1 and reviews["replayed"]["replayed_prior_receipt_count"] == 11,
        "no_candidate_produces_no_review": not reviews["none"]["candidate_available"],
        "tampered_continuity_discards_review": not reviews["tampered"]["candidate_available"],
        "completed_handoff_is_valid_and_eligible": handoffs["completed"]["valid"] and handoffs["completed"]["eligible"],
        "handoff_requires_provider_completion": not handoffs["before_provider"]["eligible"],
        "handoff_requires_memory_commit": not handoffs["before_memory_commit"]["eligible"],
        "all_handoffs_are_content_free": all(row["content_free"] for row in handoffs.values()),
        "all_handoffs_preserve_authority": all(row["authority_preserved"] for row in handoffs.values()),
        "clean_state_is_reliable": reliability["reliable"]["valid"] and reliability["reliable"]["ordinary_conversation_ready"],
        "replay_is_visible_without_recovery": reliability["replayed"]["valid"] and reliability["replayed"]["ordinary_conversation_ready"],
        "tampered_receipt_fails_closed": reliability["tampered"]["valid"] and not reliability["tampered"]["ordinary_conversation_ready"],
        "receipt_flood_fails_closed": reliability["flood"]["valid"] and reliability["flood"]["receipt_budget_exceeded"] and not reliability["flood"]["candidate_available"],
        "recovered_projection_residue_fails_closed": reliability["recovered_residue"]["valid"] and reliability["recovered_residue"]["residual_candidate_detected"],
        "all_reliability_outputs_are_content_free": all(row["content_free"] for row in reliability.values()),
        "all_reliability_outputs_preserve_authority": all(row["authority_preserved"] for row in reliability.values()),
        "verified_receipt_resumes_once": receipt_rows["verified"]["verified_receipt_count"] == 1,
        "replayed_receipt_does_not_amplify": receipt_rows["replayed"]["verified_receipt_count"] == 1 and receipt_rows["replayed"]["replayed_receipt_count"] == 1,
        "tampered_receipt_requires_recovery": receipt_rows["tampered"]["recovery_required"],
        "stale_receipt_is_suppressed": receipt_rows["stale"]["stale_receipt_count"] == 1 and receipt_rows["stale"]["verified_receipt_count"] == 0,
        "receipt_budget_is_enforced": receipt_rows["flood"]["receipt_budget_exceeded"],
        "private_canaries_are_absent": not any(
            token in json.dumps((projections, reviews, handoffs, reliability, receipt_rows), sort_keys=True)
            for token in _FORBIDDEN_REPORT_VALUES[:4]
        ),
    }
    return {
        "checks": checks,
        "passed": sum(bool(value) for value in checks.values()),
        "total": len(checks),
        "projection_case_count": len(projections),
        "review_case_count": len(reviews),
        "handoff_case_count": len(handoffs),
        "reliability_case_count": len(reliability),
        "receipt_case_count": len(receipt_rows),
        "projection_summaries": projections,
        "review_summaries": reviews,
        "handoff_summaries": handoffs,
        "reliability_summaries": reliability,
        "receipt_summaries": receipt_rows,
        "content_free": True,
        "structural_digest": _digest({
            "checks": checks, "projections": projections, "reviews": reviews,
            "handoffs": handoffs, "reliability": reliability, "receipts": receipt_rows,
        }),
    }


@lru_cache(maxsize=8)
def _static_source_evidence(source_text: str, source_signature: str) -> str:
    del source_signature
    source = Path(source_text)
    runtime_text = (source / "conscious_agent" / "conversation_runtime.py").read_text(encoding="utf-8")
    goal_text = (source / "conscious_agent" / "internally_generated_goal_runtime.py").read_text(encoding="utf-8")
    integration = {
        "ordinary_runtime_builds_goal_projection_in_both_paths": runtime_text.count("build_internally_generated_goal_candidate(") == 2,
        "ordinary_runtime_builds_review_projection_in_both_paths": runtime_text.count("build_internally_generated_goal_candidate_review_projection(") == 2,
        "ordinary_runtime_builds_reliability_in_both_paths": runtime_text.count("build_internally_generated_goal_candidate_reliability(") == 2,
        "ordinary_runtime_builds_completion_handoff_in_both_paths": runtime_text.count("build_internally_generated_goal_candidate_review_handoff(") == 2,
        "ordinary_runtime_applies_goal_prompt_in_both_paths": runtime_text.count('goal_candidate_projection["prompt_section"]') == 2,
        "ordinary_runtime_applies_review_prompt_in_both_paths": runtime_text.count('goal_candidate_review_projection["prompt_section"]') == 2,
        "ordinary_runtime_reports_goal_policy_in_both_paths": runtime_text.count('["internally_generated_goal_candidate_policy"]') == 2,
        "ordinary_runtime_reports_review_packet_in_both_paths": runtime_text.count('["internally_generated_goal_candidate_review_packet"]') == 2,
        "ordinary_runtime_reports_reliability_in_both_paths": runtime_text.count('["internally_generated_goal_candidate_reliability"]') == 2,
        "ordinary_runtime_preserves_prior_goal_receipts": runtime_text.count("prior_goal_candidate_receipts=session_history") >= 4,
        "goal_module_reuses_historical_v1133_vocabulary": "Retained v1133 goal-governance vocabularies" in goal_text and "SOURCE_CATEGORIES" in goal_text,
        "goal_module_has_no_goal_activation_or_planning_call": all(token not in goal_text for token in (
            "activate_goal(", "create_plan(", "execute_tool(", "run_tool(", "initiate_new_turn(",
        )),
        "goal_module_has_no_provider_or_training_dependency": all(token not in goal_text.lower() for token in (
            "ollama", "openai", "sentence_transformers", "fine_tune", "model_weights =",
        )),
    }
    payload = {
        "registry": inspect_checkpoint_registry(source_root=source),
        "privacy_policy": source_only_entry_policy(),
        "privacy": package_privacy_summary_for_root(source),
        "integration": integration,
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)


def build_internally_generated_goal_candidate_checkpoint(
    runtime_root: str | Path | None = None,
    *,
    source_root: str | Path | None = None,
) -> dict[str, Any]:
    source = Path(source_root or Path(__file__).resolve().parents[1]).expanduser().resolve()
    runtime = Path(runtime_root or os.environ.get("EIDOLON_DATA_DIR") or source / "data").expanduser().resolve()
    source_before = _tree_signature(source, source_tree=True)
    runtime_before = _tree_signature(runtime, source_tree=False)

    static = json.loads(_static_source_evidence(str(source), source_before))
    synthetic = _synthetic_contract_evidence()
    registry = static["registry"]
    privacy_policy = static["privacy_policy"]
    privacy = static["privacy"]
    integration = static["integration"]
    limitations = [
        {"limitation_id": "goal_candidates_remain_structural_and_content_free", "status": "open", "current_behavior": "classes_bands_counts_booleans_and_digests_only"},
        {"limitation_id": "goal_candidates_cannot_activate_themselves", "status": "open", "current_behavior": "operator_review_and_approval_required"},
        {"limitation_id": "durable_goal_creation_is_not_implemented", "status": "open", "current_behavior": "review_candidate_only"},
        {"limitation_id": "hierarchical_planning_has_not_started", "status": "open", "next_action": "begin_only_v1171_after_operator_acceptance"},
        {"limitation_id": "checkpoint_does_not_validate_native_provider_behavior", "status": "open", "current_behavior": "provider_neutral_read_only_evidence"},
        {"limitation_id": "native_desktop_verification_pending", "status": "open", "next_action": "defer_desktop_codex_review_until_v1200"},
    ]
    registry_row = next(
        (row for row in registry.get("checkpoints", []) if row.get("checkpoint_id") == "internally-generated-goal-candidate-checkpoint"),
        None,
    )
    checks: list[tuple[str, bool]] = [
        *[(name, bool(value)) for name, value in synthetic["checks"].items()],
        *[(name, bool(value)) for name, value in integration.items()],
        ("checkpoint_registry_discovers_internally_generated_goal_candidate_checkpoint", registry_row is not None
         and registry_row.get("builder") == "build_internally_generated_goal_candidate_checkpoint"
         and int(registry.get("checkpoint_count") or 0) >= 197
         and not registry.get("duplicate_checkpoint_ids") and not registry.get("duplicate_builder_targets")),
        ("source_only_policy_excludes_runtime_data", privacy_policy.get("excludes_all_data_directory_entries") is True
         and not privacy_policy.get("authorizes_package_creation") and not privacy_policy.get("publishes_release")),
        ("current_source_tree_privacy_scan_passes", privacy.get("ok") is True and privacy.get("source_only") is True
         and privacy.get("forbidden_count") == 0 and privacy.get("private_content_finding_count") == 0),
        ("remaining_limitations_are_explicit", len(limitations) == 6 and all(row.get("status") == "open" for row in limitations)),
        ("checkpoint_does_not_modify_source_or_runtime", source_before == _tree_signature(source, source_tree=True)
         and runtime_before == _tree_signature(runtime, source_tree=False)),
    ]
    rows = [{"check_id": name, "status": "pass" if value else "fail"} for name, value in checks]
    ok = all(value for _, value in checks)
    report: dict[str, Any] = {
        "contract_version": CONTRACT_VERSION,
        "checkpoint_id": _CHECKPOINT_ID,
        "ok": ok,
        "status": "internally_generated_goal_candidate_checkpoint_candidate" if ok else "review_required",
        "passed": sum(bool(value) for _, value in checks),
        "total": len(checks),
        "checks": rows,
        "summary": {
            "synthetic_contract_check_count": synthetic["total"],
            "projection_case_count": synthetic["projection_case_count"],
            "review_case_count": synthetic["review_case_count"],
            "handoff_case_count": synthetic["handoff_case_count"],
            "reliability_case_count": synthetic["reliability_case_count"],
            "receipt_case_count": synthetic["receipt_case_count"],
            "registered_checkpoint_count": registry.get("checkpoint_count", 0),
            "component_maximum_bytes": MAX_COMPONENT_BYTES,
            "current_message_maximum_bytes": MAX_CURRENT_MESSAGE_BYTES,
            "observation_row_maximum_count": MAX_OBSERVATION_ROWS,
            "prior_receipt_maximum_count": MAX_PRIOR_RECEIPTS,
            "receipt_maximum_bytes": MAX_RECEIPT_BYTES,
            "prompt_maximum_chars": MAX_PROMPT_CHARS,
            "evidence_maximum_count": MAX_EVIDENCE_COUNT,
            "reliability_fault_maximum_count": MAX_RELIABILITY_FAULTS,
            "authoritative_conversation_path_count": 2 if integration["ordinary_runtime_builds_reliability_in_both_paths"] else 0,
            "open_limitation_count": len(limitations),
            "privacy_forbidden_entry_count": privacy.get("forbidden_count", 0),
            "privacy_content_finding_count": privacy.get("private_content_finding_count", 0),
        },
        "evidence": {
            "synthetic_contracts": synthetic,
            "ordinary_conversation_integration": integration,
            "registry": {
                "checkpoint_count": registry.get("checkpoint_count", 0),
                "duplicate_checkpoint_id_count": len(registry.get("duplicate_checkpoint_ids") or []),
                "duplicate_builder_target_count": len(registry.get("duplicate_builder_targets") or []),
                "content_free": True,
            },
            "privacy": {
                "source_only": privacy.get("source_only"),
                "forbidden_count": privacy.get("forbidden_count", 0),
                "private_content_finding_count": privacy.get("private_content_finding_count", 0),
                "structural_digest": privacy.get("structural_digest", ""),
                "content_free": True,
            },
        },
        "remaining_limitations": limitations,
        "read_only": True,
        "post_available": False,
        "content_free": True,
        "authority_preserved": True,
        "operator_promotion_required": True,
        "desktop_verification_deferred_until_v1200": True,
        "native_provider_certification_pending": True,
        "internally_generated_goal_candidate_checkpoint_completed": ok,
        "goal_nomination_review_continuity_and_reliability_consolidated": True,
        "historical_v1133_goal_governance_preserved": True,
        "literal_current_request_precedence_preserved": True,
        "goal_activation_not_started": True,
        "hierarchical_planning_not_started": True,
        "tools_and_actions_not_started": True,
        "uncontrolled_self_training_not_started": True,
        "model_training_not_started": True,
        "model_weights_unchanged": True,
        "automatic_memory_mutation_not_started": True,
        "automatic_lesson_commit_not_started": True,
        "raw_conversation_exposed": False,
        "raw_message_exposed": False,
        "goal_text_exposed": False,
        "memory_content_exposed": False,
        "lesson_content_exposed": False,
        "prompt_exposed": False,
        "provider_payload_exposed": False,
        "operation_identifiers_exposed": False,
        "session_identifiers_exposed": False,
        "hidden_reasoning_exposed": False,
        "consciousness_proven": False,
        "sentience_proven": False,
        "personhood_proven": False,
    }
    for field in (
        "provider_contacted", "embedding_model_contacted", "command_executed", "action_executed",
        "message_sent", "notification_created", "goal_created", "goal_modified", "goal_activated",
        "plan_created", "decision_created", "intention_created", "tool_routed", "tool_executed",
        "source_edit_performed", "approval_request_created", "approval_created", "approval_granted",
        "authorization_created", "installation_performed", "upgrade_performed", "rollback_performed",
        "packaging_performed", "promotion_performed", "certification_performed",
        "proactive_turn_created", "memory_mutated", "memory_record_deleted", "memory_record_retracted",
        "lesson_created", "lesson_committed", "model_training_performed", "self_training_performed",
        "automatic_generalization_performed", "model_weights_changed", "response_rewritten",
    ):
        report[field] = False
    report["structural_digest"] = _digest({
        "contract_version": CONTRACT_VERSION,
        "checks": rows,
        "summary": report["summary"],
        "limitations": limitations,
        "synthetic_digest": synthetic["structural_digest"],
    })
    serialized = json.dumps(report, sort_keys=True)
    report["forbidden_report_value_count"] = sum(serialized.count(token) for token in _FORBIDDEN_REPORT_VALUES)
    if report["forbidden_report_value_count"]:
        report["ok"] = False
        report["status"] = "review_required"
    return report
